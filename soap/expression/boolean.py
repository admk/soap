"""
.. module:: soap.expression.boolean
    :synopsis: The class of boolean expressions.
"""
from soap.expression import operators
from soap.expression.base import (
    Expression, UnaryExpression, BinaryExpression, TernaryExpression
)


class BoolExpr(Expression):
    """The boolean expression class."""

    __slots__ = ()

    def __init__(self, op=None, *args, top=False, bottom=False):
        if not top and not bottom and op not in operators.BOOLEAN_OPERATORS:
            raise ValueError('Boolean expression must use a boolean operator.')
        super().__init__(op, *args, top=top, bottom=bottom)

    def __invert__(self):
        return UnaryBoolExpr(op=operators.UNARY_NEGATION_OP, a=self)

    def __and__(self, other):
        return BinaryBoolExpr(op=operators.AND_OP, a1=self, a2=other)

    def __or__(self, other):
        return BinaryBoolExpr(op=operators.OR_OP, a1=self, a2=other)


class UnaryBoolExpr(UnaryExpression, BoolExpr):
    """Unary boolean expressions."""

    __slots__ = ()


class BinaryBoolExpr(BinaryExpression, BoolExpr):
    """Binary boolean expressions."""

    __slots__ = ()


class TernaryBoolExpr(TernaryExpression, BoolExpr):
    """Ternary boolean expressions."""

    __slots__ = ()
