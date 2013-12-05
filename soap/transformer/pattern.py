import collections
import itertools

from patmat.mimic import _Mimic, Val

from soap.common import cached
from soap.expression.common import (
    is_expr, is_variable, is_constant, expression_factory,
)
from soap.expression.operators import ASSOCIATIVITY_OPERATORS
from soap.expression.parser import parse


class ExprMimic(_Mimic):
    def __init__(self, op, args):
        super().__init__()
        self.op = op
        self.args = args

    def _initial_match(self, other, env):
        if not is_expr(other):
            return False
        if not self._match_item(self.op, other.op, env):
            return False
        return True

    def _match(self, other, env):
        if not self._initial_match(other, env):
            return False
        if other.op in ASSOCIATIVITY_OPERATORS:
            other_args_permutations = itertools.permutations(other.args)
        else:
            other_args_permutations = [other.args]
        for other_args in other_args_permutations:
            args_env = dict(env)
            for sa, oa in zip(self.args, other_args):
                if not self._match_item(sa, oa, args_env):
                    break
            else:  # everything matches
                env.update(args_env)
                break
        else:  # tried all permutations, no match found
            return False
        return True

    def __hash__(self):
        return hash(expression_factory(self.op, *self.args))

    def __repr__(self):
        return '{cls}(op={op!r}, args={args!r})'.format(
            cls=self.__class__.__name__, op=self.op, args=self.args)


class ExprConstPropMimic(ExprMimic):
    def __init__(self):
        super().__init__(op=Val('op'), args=None)

    def _match(self, other, env):
        if not self._initial_match(other, env):
            return False
        if not isinstance(other.args, collections.Sequence):
            return False
        if not all(is_constant(a) for a in other.args):
            return False
        env['args'] = other.args
        return True


def compile(*expressions):
    def _compile(expression):
        if isinstance(expression, str):
            return _compile(parse(expression))
        if is_expr(expression):
            return ExprMimic(
                expression.op, [_compile(a) for a in expression.args])
        if is_variable(expression):
            return Val(expression.name)
        if is_constant(expression):
            return expression
        if isinstance(expression, ExprMimic):
            return expression
        if callable(expression):
            return expression
        raise ValueError(
            'Do not know how to convert {!r} to an ExprMimic instance.'
            ''.format(expression))
    return [_compile(e) for e in expressions]


@cached
def decompile(mimic, env):
    if isinstance(mimic, ExprMimic):
        return expression_factory(
            mimic.op, *(decompile(a, env) for a in mimic.args))
    if isinstance(mimic, Val):
        return env[mimic.name]
    if is_constant(mimic):
        return mimic
    raise ValueError(
        'Do not know how to convert {!r} to an Expression instance.'
        ''.format(mimic))


def transform(rule, expression):
    patterns, matches, name = rule
    concrete_matches = set()
    for p in patterns:
        env = p.match(expression)
        if not env:
            continue
        for m in matches:
            m = m(**env) if callable(m) else decompile(m, env)
            concrete_matches.add(m)
    return concrete_matches


def transformer_factory(rule):
    """Create a function that transforms an expression from the given rule.

    :func:`functools.partial` is used instead of lambda to support pickling.
    """
    from functools import partial
    return partial(transform, rule=rule)
