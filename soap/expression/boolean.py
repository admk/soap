"""
.. module:: soap.expression.boolean
    :synopsis: The class of boolean expressions.
"""
from soap.expression.operators import (
    EQUAL_OP, GREATER_OP, LESS_OP, UNARY_NEGATION_OP, AND_OP, OR_OP,
    BOOLEAN_OPERATORS
)
from soap.expression.base import (
    Expression, UnaryExpression, BinaryExpression, TernaryExpression
)


class BoolExpr(Expression):
    """The boolean expression class."""

    __slots__ = ()

    def __init__(self, op, *args):
        if op not in BOOLEAN_OPERATORS:
            raise ValueError('Boolean expression must use a boolean operator.')
        super().__init__(op, *args)

    def __invert__(self):
        return UnaryBoolExpr(op=UNARY_NEGATION_OP, a=self)

    def __and__(self, other):
        return BinaryBoolExpr(op=AND_OP, a1=self, a2=other)

    def __or__(self, other):
        return BinaryBoolExpr(op=OR_OP, a1=self, a2=other)


class UnaryBoolExpr(UnaryExpression, BoolExpr):
    """Unary boolean expressions."""

    __slots__ = ()


class BinaryBoolExpr(BinaryExpression, BoolExpr):
    """Binary boolean expressions."""

    __slots__ = ()


class TernaryBoolExpr(TernaryExpression, BoolExpr):
    """Ternary boolean expressions."""

    __slots__ = ()
