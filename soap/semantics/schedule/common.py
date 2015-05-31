import math

import islpy

from soap.expression import (
    expression_factory, is_expression, is_variable, Variable, operators
)


NONPIPELINED_OPERATORS = {
    operators.INDEX_ACCESS_OP,
    operators.INDEX_UPDATE_OP,
    operators.FIXPOINT_OP,
}
PIPELINED_OPERATORS = set(operators.OPERATORS) - NONPIPELINED_OPERATORS


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
