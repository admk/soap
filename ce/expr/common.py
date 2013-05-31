ADD_OP = '+'
MULTIPLY_OP = '*'
BARRIER_OP = '|'

OPERATORS = [ADD_OP, MULTIPLY_OP, BARRIER_OP]

ASSOCIATIVITY_OPERATORS = [ADD_OP, MULTIPLY_OP]

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


def is_expr(e):
    from ce.expr.biop import Expr
    return isinstance(e, Expr)


def concat_multi_expr(*expr_args):
    from ce.expr.biop import Expr
    me = None
    for e in expr_args:
        e = Expr(e)
        me = me | e if me else e
    return me


def split_multi_expr(e):
    if e.op != BARRIER_OP:
        return [e]
    return split_multi_expr(e.a1) + split_multi_expr(e.a2)
