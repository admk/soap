"""
.. module:: soap.expression.arithmetic
    :synopsis: The class of expressions.
"""
from soap.expression.operators import (
    ADD_OP, SUBTRACT_OP, MULTIPLY_OP, DIVIDE_OP, UNARY_SUBTRACT_OP,
    TERNARY_SELECT_OP, ARITHMETIC_OPERATORS, COMMUTATIVITY_OPERATORS
)
from soap.expression.base import (
    Expression, UnaryExpression, BinaryExpression, TernaryExpression,
    QuaternaryExpression
)


class ArithmeticMixin(object):

    def __add__(self, other):
        return BinaryArithExpr(ADD_OP, self, other)

    def __sub__(self, other):
        return BinaryArithExpr(SUBTRACT_OP, self, other)

    def __mul__(self, other):
        return BinaryArithExpr(MULTIPLY_OP, self, other)

    def __div__(self, other):
        return BinaryArithExpr(DIVIDE_OP, self, other)

    def __neg__(self):
        return UnaryArithExpr(UNARY_SUBTRACT_OP, self)


class ArithExpr(ArithmeticMixin, Expression):
    """Base class for arithmetic expressions."""

    __slots__ = ()

    def __init__(self, op, *args):
        if op not in ARITHMETIC_OPERATORS:
            raise ValueError(
                'ArithExpr expression must use an arithmetic operator.')
        super().__init__(op, *args)


class UnaryArithExpr(UnaryExpression, ArithExpr):
    """Unary arithmetic expressions."""

    __slots__ = ()
    _str_brackets = False

    def format(self):
        arg, = self._args_to_str()
        if self.op == UNARY_SUBTRACT_OP:
            return '-{}'.format(arg)
        return super().format()


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

    def __init__(self, a1, a2, a3):
        super().__init__(TERNARY_SELECT_OP, a1, a2, a3)

    @property
    def bool_expr(self):
        return self.a1

    @property
    def true_expr(self):
        return self.a2

    @property
    def false_expr(self):
        return self.a3

    def format(self):
        return '{} ? {} : {}'.format(*self._args_to_str())
