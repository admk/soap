"""
.. module:: soap.expression.common
    :synopsis: Common definitions for expressions.
"""
from soap.common.cache import cached


ADD_OP = '+'
SUBTRACT_OP = '-'
UNARY_SUBTRACT_OP = '-'
MULTIPLY_OP = '*'
DIVIDE_OP = '/'

EQUAL_OP = '=='
NOT_EQUAL_OP = '!='
GREATER_OP = '>'
GREATER_EQUAL_OP = '>='
LESS_OP = '<'
LESS_EQUAL_OP = '<='
UNARY_NEGATION_OP = '~'
AND_OP = '&'
OR_OP = '|'

BARRIER_OP = '//'

BOOLEAN_OPERATORS = [
    EQUAL_OP, NOT_EQUAL_OP, GREATER_OP, LESS_OP, GREATER_EQUAL_OP,
    LESS_EQUAL_OP, UNARY_NEGATION_OP, AND_OP, OR_OP
]
ARITHMETIC_OPERATORS = [
    ADD_OP, SUBTRACT_OP, UNARY_SUBTRACT_OP, MULTIPLY_OP, DIVIDE_OP
]
OPERATORS = BOOLEAN_OPERATORS + ARITHMETIC_OPERATORS
UNARY_OPERATORS = [UNARY_SUBTRACT_OP, UNARY_NEGATION_OP]

ASSOCIATIVITY_OPERATORS = [ADD_OP, MULTIPLY_OP, EQUAL_OP, AND_OP, OR_OP]

COMMUTATIVITY_OPERATORS = ASSOCIATIVITY_OPERATORS

COMMUTATIVE_DISTRIBUTIVITY_OPERATOR_PAIRS = [(MULTIPLY_OP, ADD_OP)]
# left-distributive: a * (b + c) == a * b + a * c
LEFT_DISTRIBUTIVITY_OPERATOR_PAIRS = \
    COMMUTATIVE_DISTRIBUTIVITY_OPERATOR_PAIRS
# Note that division '/' is only right-distributive over +
RIGHT_DISTRIBUTIVITY_OPERATOR_PAIRS = \
    COMMUTATIVE_DISTRIBUTIVITY_OPERATOR_PAIRS

LEFT_DISTRIBUTIVITY_OPERATORS, LEFT_DISTRIBUTION_OVER_OPERATORS = \
    list(zip(*LEFT_DISTRIBUTIVITY_OPERATOR_PAIRS))
RIGHT_DISTRIBUTIVITY_OPERATORS, RIGHT_DISTRIBUTION_OVER_OPERATORS = \
    list(zip(*RIGHT_DISTRIBUTIVITY_OPERATOR_PAIRS))


op_func_dict_by_ary_list = [
    {
        UNARY_SUBTRACT_OP: lambda x, _: -x,
    },
    {
        ADD_OP: lambda x, y: x + y,
        SUBTRACT_OP: lambda x, y: x - y,
        MULTIPLY_OP: lambda x, y: x * y,
        DIVIDE_OP: lambda x, y: x / y,
        LESS_OP: lambda x, y: x < y,
        LESS_EQUAL_OP: lambda x, y: x <= y,
        EQUAL_OP: lambda x, y: x == y,
        GREATER_EQUAL_OP: lambda x, y: x >= y,
        GREATER_OP: lambda x, y: x > y,
    }
]


def is_variable(e):
    from soap.expression.variable import Variable
    return isinstance(e, Variable)


def is_constant(e):
    from soap.semantics.error import mpz_type, mpfr_type
    return isinstance(e, (mpz_type, mpfr_type))


def is_expr(e):
    from soap.expression.base import Expression
    return isinstance(e, Expression)


def is_arith_expr(e):
    """Check if `e` is an expression."""
    from soap.expression.arithmetic import ArithExpr
    return isinstance(e, ArithExpr)


def is_bool_expr(e):
    """Check if `e` is a boolean expression."""
    from soap.expression.boolean import BoolExpr
    return isinstance(e, BoolExpr)


def concat_multi_expr(*expr_args):
    """Concatenates multiple expressions into a single expression by using the
    barrier operator.
    """
    me = None
    for e in expr_args:
        me = me | e if me else e
    return me


def split_multi_expr(e):
    """Splits the single expression into multiple expressions."""
    if e.op != BARRIER_OP:
        return [e]
    return split_multi_expr(e.a1) + split_multi_expr(e.a2)


@cached
def expression_factory(op, *args):
    from soap.expression.base import Variable
    from soap.expression.arithmetic import (
        UnaryArithExpr, BinaryArithExpr, TernaryArithExpr
    )
    from soap.expression.boolean import (
        UnaryBoolExpr, BinaryBoolExpr, TernaryBoolExpr
    )
    if not args:
        if not isinstance(op, str):
            raise ValueError('Do not know how to construct expression from '
                             '{!r}'.format(op))
        return Variable(op)
    if op in ARITHMETIC_OPERATORS:
        class_list = [UnaryArithExpr, BinaryArithExpr, TernaryArithExpr]
    elif op in BOOLEAN_OPERATORS:
        class_list = [UnaryBoolExpr, BinaryBoolExpr, TernaryBoolExpr]
    else:
        raise ValueError('Unknown operator {}.'.format(op))
    try:
        cls = class_list[len(args) - 1]
    except IndexError:
        raise ValueError('Too many arguments.')
    return cls(op, *args)
