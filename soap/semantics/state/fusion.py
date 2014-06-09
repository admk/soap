import collections

from soap import logger
from soap.expression import (
    is_variable, is_expression,
    InputVariableTuple, OutputVariableTuple, SelectExpr, FixExpr
)
from soap.label import Label
from soap.program.graph import (
    DependencyGraph, CyclicGraphException
)
from soap.semantics.common import is_numeral
from soap.semantics.state.meta import MetaState


def sorted_args(expr):
    if not expr or is_variable(expr) or is_numeral(expr):
        return []
    if isinstance(expr, (Label, OutputVariableTuple)):
        return [expr]
    if isinstance(expr, InputVariableTuple):
        return list(expr.args)
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


def inner_fusion(env, bool_expr, loop_state, loop_vars, init_state, out_vars):
    # is FixExpr, fuse stuff in environments
    ori_loop_vars = loop_vars
    if not isinstance(loop_vars, OutputVariableTuple):
        loop_vars = [loop_vars]
    loop_state = recursive_fusion(loop_state, loop_vars)
    init_state = recursive_fusion(init_state, loop_vars)
    # update env with new expr, no dependency cycles created
    expr = FixExpr(
        bool_expr, loop_state, ori_loop_vars, init_state)
    env[out_vars] = expr
    return env


def loop_fusion(env, expr):
    # not fixpoint expression
    if not isinstance(expr, FixExpr):
        return env

    # discover things to collect
    # possible FIXME: greedy collection, possibly making other things
    # unable to collect if done greedily
    bool_expr = expr.bool_expr
    loop_state = expr.loop_state
    init_state = expr.init_state

    bool_expr_vars = {var for var in bool_expr[1].values()}
    state_filter = lambda state: {
        k: v for k, v in state.items() if v in bool_expr_vars}

    # bool_expr % init_state
    init_bool_state = state_filter(init_state)
    # bool_expr % loop_state
    loop_bool_state = state_filter(loop_state)

    def merge_check(merge_var, merge_expr):
        if isinstance(merge_var, OutputVariableTuple):
            # merged, no further merging necessary
            return False
        if not isinstance(merge_expr, FixExpr):
            # not fixpoint expression
            return False

        merge_expr_bool_expr = expr.bool_expr
        if merge_expr_bool_expr != bool_expr:
            # bool_expr is different
            return False

        if init_bool_state != state_filter(merge_expr.init_state):
            # input values for bool_expr is different
            return False

        if loop_bool_state != state_filter(merge_expr.loop_state):
            # output values from loop exit for next iteration's bool_expr is
            # different
            return False

        return True

    fused_loop_state = MetaState.empty()
    fused_init_state = MetaState.empty()
    loop_vars = []
    out_vars = []

    for each_var, each_expr in sorted(env.items(), key=str):
        if not merge_check(each_var, each_expr):
            continue
        loop_vars.append(each_expr.loop_var)
        out_vars.append(each_var)
        fused_loop_state |= each_expr.loop_state
        fused_init_state |= each_expr.init_state

    loop_vars = OutputVariableTuple(loop_vars)
    out_vars = OutputVariableTuple(out_vars)

    if len(loop_vars) <= 1:
        # did not merge
        return env

    # check for merge conflicts
    conflict_check = lambda state: any(
        expr.is_top() for expr in state.values())
    if conflict_check(fused_loop_state) or conflict_check(fused_init_state):
        # merge conflicts
        return env

    new_env = dict(env)

    fix_expr = FixExpr(
        bool_expr, fused_loop_state, loop_vars, fused_init_state)
    new_env[out_vars] = fix_expr

    for var in out_vars:
        new_env[var] = out_vars

    return new_env


def recursive_fusion(env, out_vars):
    def acyclic_assign(fusion_func, env, expr):
        new_env = fusion_func(env, expr)
        if env == new_env:
            return env
        try:
            DependencyGraph(new_env, out_vars)
        except CyclicGraphException:
            return env
        return new_env

    for var in out_vars:
        # InputVariableTuple
        if isinstance(var, InputVariableTuple):
            env = recursive_fusion(env, var)
            continue

        expr = env.get(var)
        if expr is None:
            continue

        # fusion kernel
        env = acyclic_assign(branch_fusion, env, expr)
        env = acyclic_assign(loop_fusion, env, expr)

        if not isinstance(expr, FixExpr):
            # depth-first recursively merge branches
            env = recursive_fusion(env, sorted_args(expr))
            continue

        # is fixpoint expression, fuse stuff in local environments
        expr = env.get(var)
        if isinstance(expr, OutputVariableTuple):
            # if already fused, get fused fixpoint expression
            var = expr
            expr = env.get(expr)
            if not isinstance(expr, FixExpr):
                raise TypeError(
                    'FixExpr expected for OutputVariableTuple of variable {}.'
                    .format(var))

        ori_loop_var = loop_var = expr.loop_var
        if not isinstance(loop_var, OutputVariableTuple):
            loop_var = [loop_var]
        loop_state = recursive_fusion(expr.loop_state, loop_var)
        init_state = recursive_fusion(expr.init_state, loop_var)
        # update env with new expr, no dependency cycles created
        expr = FixExpr(
            expr.bool_expr, loop_state, ori_loop_var, init_state)
        env[var] = expr

    return env


def fusion(env, out_vars):
    if not out_vars:
        logger.error(
            'Expect out_vars to be provided, using env.keys() instead, '
            'may introduce nondeterminism in fusion.')
        out_vars = env.keys()
    elif not isinstance(out_vars, collections.Sequence):
        logger.error(
            'Expect out_vars to be a sequence, '
            'may introduce nondeterminism in fusion.')
    return recursive_fusion(env, out_vars)
