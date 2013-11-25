from soap.common import cached
from soap.expression.common import (
    is_expr, is_variable, is_constant, expression_factory
)
from soap.expression.parser import parse
from soap.patmat.mimic import _Mimic, Val


class _ExprMimic(_Mimic):
    def __init__(self, op, *args):
        self.op = op
        self.args = args

    def _match(self, other, env=None):
        if not is_expr(other):
            return False
        if self.op != other.op:
            return False
        for sa, oa in zip(self.args, other.args):
            if not self._match_item(sa, oa, env):
                return False
        return True

    def __hash__(self):
        return hash(expression_factory(self.op, *self.args))


def abstract(expression):
    if is_expr(expression):
        return _ExprMimic(
            expression.op, *(abstract(a) for a in expression.args))
    if is_variable(expression):
        return Val(expression.n)
    if is_constant(expression):
        return expression
    raise ValueError(
        'Do not know how to convert {} to a _ExprMimic instance.'
        ''.format(expression))


@cached
def concretize(mimic, env):
    if isinstance(mimic, _ExprMimic):
        return expression_factory(
            mimic.op, *(concretize(a, env) for a in mimic.args))
    if isinstance(mimic, Val):
        return env[mimic.name]
    if is_constant(mimic):
        return mimic
    raise ValueError(
        'Do not know how to convert {} to an Expression instance.'
        ''.format(mimic))


def pattern_transformer_factory(patterns, matches, name):
    patterns = (abstract(parse(p)) for p in patterns)
    matches = (abstract(parse(m)) for m in matches)

    def transform(expression):
        concrete_matches = set()
        for p in patterns:
            env = p.match(expression)
            if not env:
                continue
            for m in matches:
                concrete_matches.add(concretize(m, env))
        return concrete_matches

    transform.__name__ = name
    return transform
