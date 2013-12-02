from patmat.mimic import _Mimic, Val, Pred

from soap.common import cached
from soap.expression.common import (
    is_expr, is_variable, is_constant, expression_factory
)
from soap.expression.parser import parse


class ExprMimic(_Mimic):
    def __init__(self, op, args):
        super().__init__()
        self.op = op
        self.args = args

    def _match(self, other, env=None):
        if not is_expr(other):
            return False
        if not self._match_item(self.op, other.op, env):
            return False
        for sa, oa in zip(self.args, other.args):
            if not self._match_item(sa, oa, env):
                return False
        return True

    def __hash__(self):
        return hash(expression_factory(self.op, *self.args))

    def __repr__(self):
        return '{cls}(op={op!r}, args={args!r})'.format(
            cls=self.__class__.__name__, op=self.op, args=self.args)


class ConstVal(Val):
    def __init__(self, value):
        super().__init__(value)

    def _match(self, other, env):
        if not is_constant(other):
            return False
        return super()._match(other, env)


def compile(*expressions):
    def _compile(expression):
        if isinstance(expression, str):
            return _compile(parse(expression))
        if is_expr(expression):
            return ExprMimic(
                expression.op, [_compile(a) for a in expression.args])
        if is_variable(expression):
            return Val(expression.n)
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
