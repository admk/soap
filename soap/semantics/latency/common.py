import math

import islpy

from soap.expression import (
    expression_factory, InputVariable, is_expression, is_variable, Variable,
)
from soap.semantics import is_numeral, Label, IntegerInterval


class DependenceType(object):
    independent = 0
    flow = 1
    anti = 2
    output = 3


def stitch_expr(expr, env):
    if is_expression(expr):
        args = (stitch_expr(a, env) for a in expr.args)
        return expression_factory(expr.op, *args)
    if isinstance(expr, Label):
        return stitch_expr(env[expr], env)
    if is_numeral:
        return expr
    if isinstance(expr, InputVariable):
        return Variable(expr.name, expr.dtype)
    raise TypeError('Do not know how to stitch expression {}.'.format(expr))


def stitch_env(env):
    mapping = {
        v: stitch_expr(e, env) for v, e in env.items() if is_variable(v)
    }
    return env.__class__(mapping)


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


def iter_point_count(iter_slice, minimize):
    bound = iter_slice.stop - iter_slice.start
    if isinstance(bound, IntegerInterval):
        if minimize:
            bound = bound.min
        else:
            bound = bound.max
    return max(0, int(math.floor(bound / iter_slice.step))) + 1
