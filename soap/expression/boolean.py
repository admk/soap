"""
.. module:: soap.expression.boolean
    :synopsis: The class of boolean expressions.
"""
from soap.expression import operators
from soap.expression.base import (
    Expression, UnaryExpression, BinaryExpression, TernaryExpression
)


class BooleanMixin(object):

    def __invert__(self):
        return UnaryBoolExpr(operators.UNARY_NEGATION_OP, self)

    def __and__(self, other):
        return BinaryBoolExpr(operators.AND_OP, self, other)

    def __or__(self, other):
        return BinaryBoolExpr(operators.OR_OP, self, other)


class BoolExpr(BooleanMixin, Expression):
    """The boolean expression class."""

    __slots__ = ()

    def __init__(self, op, *args):
        if op not in operators.BOOLEAN_OPERATORS:
            raise ValueError(
                'BoolExpr expression must use a boolean operator.')
        super().__init__(op, *args)


class UnaryBoolExpr(UnaryExpression, BoolExpr):
    """Unary boolean expressions."""

    __slots__ = ()


class BinaryBoolExpr(BinaryExpression, BoolExpr):
    """Binary boolean expressions."""

    __slots__ = ()


class TernaryBoolExpr(TernaryExpression, BoolExpr):
    """Ternary boolean expressions."""

    __slots__ = ()
