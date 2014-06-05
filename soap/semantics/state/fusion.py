import collections

from soap.expression import (
    is_variable, is_expression,
    InputVariableTuple, OutputVariableTuple, SelectExpr, StateGetterExpr
)
from soap.label import Label
from soap.program.graph import (
    DependencyGraph, CyclicGraphException
)
from soap.semantics import is_numeral, MetaState


def sorted_args(expr):
    if not expr or is_variable(expr) or is_numeral(expr):
        return []
    if isinstance(expr, (Label, OutputVariableTuple)):
        return [expr]
    if isinstance(expr, InputVariableTuple):
        return list(expr.args)
    if isinstance(expr, StateGetterExpr):
        return [expr.meta_state]
    if is_expression(expr):
        return list(expr.args)
    if isinstance(expr, (dict, MetaState)):
        return []
    raise TypeError('Do not know how to find args of {!r}'.format(expr))


def branch_fusion(env, expr):

    # not if-then-else
    if not isinstance(expr, SelectExpr):
        return env

    # discover things to collect
    # possible FIXME: greedy collection, possibly making other things
    # unable to collect if done greedily
    bool_expr = expr.bool_expr
    true_env = {}
    false_env = {}
    for each_var, each_expr in env.items():
        if not isinstance(each_expr, SelectExpr):
            continue
        if each_expr.bool_expr != bool_expr:
            continue
        if isinstance(each_var, OutputVariableTuple):
            # merged, no further merging necessary
            continue
        # same bool_expr, merge together
        true_env[each_var] = each_expr.true_expr
        false_env[each_var] = each_expr.false_expr

    # did not generate collection
    if len(true_env) <= 1:
        return env

    new_env = dict(env)

    # branch expression labelling
    keys = OutputVariableTuple(sorted(true_env, key=str))
    true_values = InputVariableTuple(list(true_env[k] for k in keys))
    false_values = InputVariableTuple(list(false_env[k] for k in keys))
    branch_expr = SelectExpr(bool_expr, true_values, false_values)
    new_env[keys] = branch_expr

    # collected variables labelling
    for each_var in true_env:
        new_env[each_var] = keys

    return new_env


def loop_fusion(env, expr):
    return env


def fusion(env, out_vars):

    def acyclic_assign(fusion_func, env, expr):
        new_env = fusion_func(env, expr)
        if env == new_env:
            return env
        try:
            DependencyGraph(new_env, out_vars)
        except CyclicGraphException:
            return env
        return new_env

    if not isinstance(out_vars, collections.Sequence):
        raise TypeError('Output variables out_vars must be a sequence.')

    for var in out_vars:
        expr = env.get(var)
        env = acyclic_assign(branch_fusion, env, expr)
        env = acyclic_assign(loop_fusion, env, expr)
        # depth-first recursively merge branches
        env = fusion(env, sorted_args(expr))

    return env
