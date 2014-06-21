"""
.. module:: soap.expression.arithmetic
    :synopsis: The class of expressions.
"""
from soap.expression.operators import (
    ADD_OP, SUBTRACT_OP, MULTIPLY_OP, DIVIDE_OP, BARRIER_OP, UNARY_SUBTRACT_OP,
    TERNARY_SELECT_OP, ARITHMETIC_OPERATORS, COMMUTATIVITY_OPERATORS
)
from soap.expression.base import (
    Expression, UnaryExpression, BinaryExpression, TernaryExpression,
    QuaternaryExpression
)


class ArithmeticMixin(object):

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


class ArithExpr(ArithmeticMixin, Expression):
    """Base class for arithmetic expressions."""

    __slots__ = ()

    def __init__(self, op=None, *args, top=False, bottom=False,
                 _check_args=True):
        if _check_args:
            if not top and not bottom and op not in ARITHMETIC_OPERATORS:
                raise ValueError(
                    'ArithExpr expression must use an arithmetic operator.')
        super().__init__(
            op, *args, top=top, bottom=bottom, _check_args=_check_args)


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


class QuaternaryArithExpr(QuaternaryExpression, ArithExpr):

    __slots__ = ()


class SelectExpr(TernaryArithExpr):
    """Ternary expression with TERNARY_SELECT_OP operator."""

    __slots__ = ()

    def __init__(self, a1=None, a2=None, a3=None, top=False, bottom=False):
        super().__init__(
            op=TERNARY_SELECT_OP, a1=a1, a2=a2, a3=a3, top=top, bottom=bottom)

    @property
    def bool_expr(self):
        return self.a1

    @property
    def true_expr(self):
        return self.a2

    @property
    def false_expr(self):
        return self.a3

    def __str__(self):
        return '{} ? {} : {}'.format(*self._args_to_str())
