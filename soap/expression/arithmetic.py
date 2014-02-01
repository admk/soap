"""
.. module:: soap.expression.arithmetic
    :synopsis: The class of expressions.
"""
from soap.expression.operators import (
    ADD_OP, SUBTRACT_OP, MULTIPLY_OP, DIVIDE_OP, BARRIER_OP, UNARY_SUBTRACT_OP,
    TERNARY_SELECT_OP, ARITHMETIC_OPERATORS, COMMUTATIVITY_OPERATORS
)
from soap.expression.base import (
    Expression, UnaryExpression, BinaryExpression, TernaryExpression
)


class ArithExpr(Expression):
    """Base class for arithmetic expressions."""

    __slots__ = ()

    def __init__(self, op=None, *args, top=False, bottom=False):
        if not top and not bottom and op not in ARITHMETIC_OPERATORS:
            raise ValueError('Boolean expression must use a boolean operator.')
        super().__init__(op, *args, top=top, bottom=bottom)

    def __add__(self, other):
        return BinaryArithExpr(op=ADD_OP, a1=self, a2=other)

    def __sub__(self, other):
        return BinaryArithExpr(op=SUBTRACT_OP, a1=self, a2=other)

    def __mul__(self, other):
        return BinaryArithExpr(op=MULTIPLY_OP, a1=self, a2=other)

    def __div__(self, other):
        return BinaryArithExpr(op=DIVIDE_OP, a1=self, a2=other)

    def __floordiv__(self, other):
        return BinaryArithExpr(op=BARRIER_OP, a1=self, a2=other)

    def __neg__(self):
        return UnaryArithExpr(op=UNARY_SUBTRACT_OP, a=self)


class UnaryArithExpr(UnaryExpression, ArithExpr):
    """Unary arithmetic expressions."""

    __slots__ = ()


class BinaryArithExpr(BinaryExpression, ArithExpr):
    """Binary arithmetic expressions."""

    __slots__ = ()

    def _attr(self):
        if self.op in COMMUTATIVITY_OPERATORS:
            args = frozenset(self.args)
        else:
            args = tuple(self.args)
        return (self.op, args)


class TernaryArithExpr(TernaryExpression, ArithExpr):
    """Ternary arithmetic expressions."""

    __slots__ = ()

    def __str__(self):
        if self.op == TERNARY_SELECT_OP:
            return '{} ? {} : {}'.format(*self._args_to_str())
        return super().__str__()
