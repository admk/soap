import math

import islpy

from soap.datatype import ArrayType, int_type, real_type
from soap.expression import (
    expression_factory, is_expression, is_variable, Variable, operators
)
from soap.semantics.error import inf


# 150 MHz
LOOP_LATENCY_TABLE = {
    (int_type, operators.UNARY_SUBTRACT_OP): 0,
    (int_type, operators.LESS_OP): 1,
    (int_type, operators.LESS_EQUAL_OP): 1,
    (int_type, operators.GREATER_OP): 1,
    (int_type, operators.GREATER_EQUAL_OP): 1,
    (int_type, operators.EQUAL_OP): 1,
    (int_type, operators.NOT_EQUAL_OP): 1,
    (int_type, operators.ADD_OP): 1,
    (int_type, operators.SUBTRACT_OP): 1,
    (int_type, operators.MULTIPLY_OP): 1,
    (int_type, operators.INDEX_ACCESS_OP): 1,
    (real_type, operators.UNARY_SUBTRACT_OP): 0,
    (real_type, operators.ADD_OP): 3,
    (real_type, operators.SUBTRACT_OP): 3,
    (real_type, operators.MULTIPLY_OP): 2,
    (real_type, operators.DIVIDE_OP): 7,
    (real_type, operators.INDEX_ACCESS_OP): 1,
    (ArrayType, operators.INDEX_UPDATE_OP): 1,
    (ArrayType, operators.SUBSCRIPT_OP): 0,
}
SEQUENTIAL_LATENCY_TABLE = dict(LOOP_LATENCY_TABLE)
SEQUENTIAL_LATENCY_TABLE.update({
    (real_type, operators.ADD_OP): 4,
    (real_type, operators.SUBTRACT_OP): 4,
    (real_type, operators.MULTIPLY_OP): 3,
    (real_type, operators.DIVIDE_OP): 8,
    (real_type, operators.INDEX_ACCESS_OP): 2,
})


class DependenceType(object):
    independent = 0
    flow = 1
    anti = 2
    output = 3


def is_isl_expr(expr):
    variables = expr.vars()
    try:
        islpy.Set('{{ [{vars}]: {expr} > 0 }}'.format(
            vars=', '.join(v.name for v in variables), expr=expr))
    except islpy.Error:
        return False
    return True


def rename_var_in_expr(expr, var_list, format_str):
    if is_variable(expr):
        if expr in var_list:
            return Variable(format_str.format(expr.name), dtype=expr.dtype)
        return expr
    if is_expression(expr):
        args = (rename_var_in_expr(a, var_list, format_str)
                for a in expr.args)
        return expression_factory(expr.op, *args)
    return expr


def iter_point_count(iter_slice):
    start = iter_slice.start
    stop = iter_slice.stop
    step = iter_slice.step
    if start == -inf or stop == inf:
        raise ValueError('Unbounded iter_slice.')
    if step == 0:
        raise ZeroDivisionError('Step is 0.')
    return max(0, int(math.floor((stop - start) / step)))
