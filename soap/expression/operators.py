"""
.. module:: soap.expression.operators
    :synopsis: Common definitions for operators.
"""
# arithmetic operators
ADD_OP = '+'
SUBTRACT_OP = '-'
UNARY_SUBTRACT_OP = '_'
MULTIPLY_OP = '*'
DIVIDE_OP = '/'

# boolean operators
EQUAL_OP = '=='
NOT_EQUAL_OP = '!='
GREATER_OP = '>'
GREATER_EQUAL_OP = '>='
LESS_OP = '<'
LESS_EQUAL_OP = '<='
UNARY_NEGATION_OP = '~'
AND_OP = '&'
OR_OP = '|'

# special operators
TERNARY_SELECT_OP = '?'
FIXPOINT_OP = 'fix'
LINK_OP = '%'

BARRIER_OP = '//'


BOOLEAN_OPERATORS = [
    EQUAL_OP, NOT_EQUAL_OP, GREATER_OP, LESS_OP, GREATER_EQUAL_OP,
    LESS_EQUAL_OP, UNARY_NEGATION_OP, AND_OP, OR_OP, LINK_OP,
]
ARITHMETIC_OPERATORS = [
    ADD_OP, SUBTRACT_OP, UNARY_SUBTRACT_OP, MULTIPLY_OP, DIVIDE_OP,
    TERNARY_SELECT_OP, LINK_OP,
]

OPERATORS = BOOLEAN_OPERATORS + ARITHMETIC_OPERATORS

UNARY_OPERATORS = [UNARY_SUBTRACT_OP, UNARY_NEGATION_OP]
BINARY_OPERATORS = list(set(OPERATORS) - set(UNARY_OPERATORS))


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
