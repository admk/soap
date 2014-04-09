"""
.. module:: soap.expression.boolean
    :synopsis: The class of boolean expressions.
"""
from soap.common.cache import cached
from soap.expression import operators
from soap.expression.base import (
    Expression, UnaryExpression, BinaryExpression, TernaryExpression
)


class BooleanMixin(object):

    def __invert__(self):
        return UnaryBoolExpr(op=operators.UNARY_NEGATION_OP, a=self)

    def __and__(self, other):
        return BinaryBoolExpr(op=operators.AND_OP, a1=self, a2=other)

    def __or__(self, other):
        return BinaryBoolExpr(op=operators.OR_OP, a1=self, a2=other)


class BoolExpr(BooleanMixin, Expression):
    """The boolean expression class."""

    __slots__ = ()

    def __init__(self, op=None, *args, top=False, bottom=False,
                 _check_args=True):
        if _check_args:
            if not top and not bottom:
                if op not in operators.BOOLEAN_OPERATORS:
                    raise ValueError(
                        'BoolExpr expression must use a boolean operator.')
        super().__init__(
            op, *args, top=top, bottom=bottom, _check_args=_check_args)


class UnaryBoolExpr(UnaryExpression, BoolExpr):
    """Unary boolean expressions."""

    __slots__ = ()


class BinaryBoolExpr(BinaryExpression, BoolExpr):
    """Binary boolean expressions."""

    __slots__ = ()
    _operator_function_dictionary = {
        operators.LESS_OP: lambda x, y: x < y,
        operators.LESS_EQUAL_OP: lambda x, y: x <= y,
        operators.EQUAL_OP: lambda x, y: x == y,
        operators.GREATER_EQUAL_OP: lambda x, y: x >= y,
        operators.GREATER_OP: lambda x, y: x > y,
    }

    @cached
    def eval(self, state):
        a1, a2 = [a.eval(state) for a in self.args]
        try:
            op = self._operator_function_dictionary[self.op]
        except KeyError:
            raise KeyError('Unrecognized operator type {!r}'.format(self.op))
        return op(a1, a2)


class TernaryBoolExpr(TernaryExpression, BoolExpr):
    """Ternary boolean expressions."""

    __slots__ = ()
