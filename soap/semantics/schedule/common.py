import math

import islpy

from soap.context import context
from soap.datatype import ArrayType, int_type, real_type
from soap.expression import (
    expression_factory, is_expression, is_variable, Variable, operators
)


NONPIPELINED_OPERATORS = {
    operators.INDEX_ACCESS_OP,
    operators.INDEX_UPDATE_OP,
    operators.FIXPOINT_OP,
}
PIPELINED_OPERATORS = set(operators.OPERATORS) - NONPIPELINED_OPERATORS

DEVICE_LATENCY_TABLE = {
    ('Virtex7', 100): {
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
        (real_type, operators.ADD_OP): 4,
        (real_type, operators.SUBTRACT_OP): 4,
        (real_type, operators.MULTIPLY_OP): 3,
        (real_type, operators.DIVIDE_OP): 8,
        (real_type, operators.INDEX_ACCESS_OP): 2,
        (ArrayType, operators.INDEX_UPDATE_OP): 1,
        (ArrayType, operators.SUBSCRIPT_OP): 0,
    },
}
DEVICE_LOOP_LATENCY_TABLE = {
    ('Virtex7', 100): {
        (real_type, operators.ADD_OP): 3,
        (real_type, operators.SUBTRACT_OP): 3,
        (real_type, operators.MULTIPLY_OP): 2,
        (real_type, operators.DIVIDE_OP): 7,
        (real_type, operators.INDEX_ACCESS_OP): 1,
    },
}


for dev_freq, table in DEVICE_LATENCY_TABLE.items():
    table = dict(table)
    table.update(DEVICE_LOOP_LATENCY_TABLE[dev_freq])
    DEVICE_LOOP_LATENCY_TABLE[dev_freq] = table

try:
    LATENCY_TABLE = DEVICE_LATENCY_TABLE[context.device, context.frequency]
    LOOP_LATENCY_TABLE = \
        DEVICE_LOOP_LATENCY_TABLE[context.device, context.frequency]
except KeyError:
    raise KeyError(
        'Device {} and frequency {} MHz combination not found.'
        .format(context.device, context.frequency))


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
    try:
        start = int(iter_slice.start)
        stop = int(iter_slice.stop)
    except OverflowError:
        raise OverflowError('Unbounded iter_slice.')
    step = iter_slice.step
    if step == 0:
        raise ZeroDivisionError('Step is 0.')
    return max(0, int(math.floor((stop - start) / step)))
