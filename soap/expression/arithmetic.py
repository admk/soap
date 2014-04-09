"""
.. module:: soap.expression.arithmetic
    :synopsis: The class of expressions.
"""
from soap.common.cache import cached
from soap.expression.operators import (
    ADD_OP, SUBTRACT_OP, MULTIPLY_OP, DIVIDE_OP, BARRIER_OP, UNARY_SUBTRACT_OP,
    TERNARY_SELECT_OP, ARITHMETIC_OPERATORS, COMMUTATIVITY_OPERATORS
)
from soap.expression.base import (
    Expression, UnaryExpression, BinaryExpression, TernaryExpression
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
    _operator_function_dictionary = {
        UNARY_SUBTRACT_OP: lambda x, _: -x,
    }

    @cached
    def eval(self, state):
        a, = self._eval_args(state)
        try:
            op = self._operator_function_dictionary[self.op]
        except KeyError:
            raise KeyError('Unrecognized operator type {!r}'.format(self.op))
        return op(a)


class BinaryArithExpr(BinaryExpression, ArithExpr):
    """Binary arithmetic expressions."""

    __slots__ = ()
    _operator_function_dictionary = {
        ADD_OP: lambda x, y: x + y,
        SUBTRACT_OP: lambda x, y: x - y,
        MULTIPLY_OP: lambda x, y: x * y,
        DIVIDE_OP: lambda x, y: x / y,
    }

    @cached
    def eval(self, state):
        a1, a2 = self._eval_args(state)
        try:
            op = self._operator_function_dictionary[self.op]
        except KeyError:
            raise KeyError('Unrecognized operator type {!r}'.format(self.op))
        return op(a1, a2)

    def _attr(self):
        if self.op in COMMUTATIVITY_OPERATORS:
            args = frozenset(self.args)
        else:
            args = tuple(self.args)
        return (self.op, args)


class TernaryArithExpr(TernaryExpression, ArithExpr):
    """Ternary arithmetic expressions."""

    __slots__ = ()


class SelectExpr(TernaryArithExpr):
    """Ternary expression with TERNARY_SELECT_OP operator."""

    __slots__ = ()

    def __init__(self, a1=None, a2=None, a3=None, top=False, bottom=False):
        super().__init__(
            op=TERNARY_SELECT_OP, a1=a1, a2=a2, a3=a3, top=top, bottom=bottom)

    @cached
    def eval(self, state):
        def eval_split(expr, state):
            return expr.eval(state) if isinstance(expr, Expression) else expr
        from soap.semantics.state.functions import bool_eval
        bool_expr, true_expr, false_expr = self.a1, self.a2, self.a3
        true_state, false_state = bool_eval(state, bool_expr)
        true_value = eval_split(true_expr, true_state)
        false_value = eval_split(false_expr, false_state)
        return true_value | false_value

    def __str__(self):
        return '{} ? {} : {}'.format(*self._args_to_str())
