"""
.. module:: soap.expr.bool
    :synopsis: The class of boolean expressions.
"""
from soap.expr.common import (
    EQUAL_OP, GREATER_OP, LESS_OP, UNARY_NEGATION_OP, AND_OP, OR_OP,
    BOOLEAN_OPERATORS
)
from soap.expr.arith import Expr


class BoolExpr(Expr):
    """The boolean expression class."""

    __slots__ = ('op', 'a1', 'a2', '_hash')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.op not in BOOLEAN_OPERATORS:
            raise ValueError('Boolean expression must use a boolean operator.')

    def __invert__(self):
        return BoolExpr(op=UNARY_NEGATION_OP, a=self)

    def __and__(self, other):
        return BoolExpr(op=AND_OP, a1=self, a2=other)

    def __or__(self, other):
        return BoolExpr(op=OR_OP, a1=self, a2=other)
