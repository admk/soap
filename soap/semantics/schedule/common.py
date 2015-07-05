import math

import islpy

from soap.common.cache import cached
from soap.expression import (
    expression_factory, is_expression, is_variable, Variable, FixExpr
)
from soap.semantics.label import Label


class DependenceType(object):
    independent = 0
    flow = 1
    anti = 2
    output = 3


def is_isl_expr(expr):
    variables = expr.vars()
    try:
        problem = '{{ [{vars}]: {expr} > 0 }}'.format(
            vars=', '.join(v.name for v in variables), expr=expr)
        islpy.Set(problem)
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


def resource_ceil(res_map):
    for dtype_op, res_count in res_map.items():
        res_map[dtype_op] = int(math.ceil(res_count))


def resource_map_add(total_map, incr_map):
    for dtype_op, res_count in incr_map.items():
        total_map[dtype_op] = total_map.setdefault(dtype_op, 0) + res_count


def resource_map_min(total_map, lower_map):
    for dtype_op, res_count in lower_map.items():
        total_map[dtype_op] = max(
            total_map.setdefault(dtype_op, 0), res_count)


@cached
def schedule_graph(expr, out_vars=None, **kwargs):
    from soap.semantics import label
    from soap.semantics.schedule.graph import (
        SequentialScheduleGraph, LoopScheduleGraph
    )
    if isinstance(expr, FixExpr):
        return LoopScheduleGraph(expr, **kwargs)
    label, env = label(expr, None, out_vars)
    if is_expression(expr):
        # expressions do not have out_vars, but have an output, in this case
        # ``label`` is its output variable
        out_vars = [label]
    return SequentialScheduleGraph(env, out_vars, **kwargs)


def label_to_expr(node):
    if isinstance(node, Label):
        node = node.expr()
    if is_expression(node):
        args = (label_to_expr(arg) for arg in node.args)
        return expression_factory(node.op, *args)
    return node
