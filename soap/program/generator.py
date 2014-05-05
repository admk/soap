import copy

from soap.expression import (
    is_variable, is_expression, expression_factory,
    Variable, SelectExpr, StateGetterExpr
)
from soap.label import Label
from soap.program.flow import (
    IdentityFlow, AssignFlow, IfFlow, CompositionalFlow
)
from soap.semantics import is_numeral


def _dataflow_dictionary(env, vars):
    """Extract dataflow from env.  """

    dataflow = {}

    for var in vars:
        expr = env.get(var)

        # find dependent variables for the corresponding expression
        if not expr:
            # can't find expression for var or var is an input variable, so
            # there are no dependencies for it
            expr_deps = set()
        elif isinstance(expr, StateGetterExpr):
            raise NotImplementedError(
                'TODO special treatment for this, because of the labelling '
                'behaviour.')
        elif is_expression(expr):
            # dependent variables in the expression
            expr_deps = expr.vars()
        elif isinstance(expr, Label) or is_variable(expr) or is_numeral(expr):
            # is a label/variable/constant, dependency is itself
            expr_deps = {expr}
        else:
            raise TypeError(
                'Do not know how to find dependencies in expression {!r}'
                .format(expr))

        # each dependency assigns the data flow direction to var
        for dep_var in expr_deps:
            dep_flow = dataflow.setdefault(dep_var, set())
            dep_flow.add(var)

        # finds the dataflow of dependent variables, except input variables
        expr_deps = {var for var in expr_deps if not is_variable(var)}
        flowflow = _dataflow_dictionary(env, expr_deps)

        # merge update dep_deps into deps
        for each_var in set(dataflow) | set(flowflow):
            each_flow = dataflow.setdefault(each_var, set())
            each_flow |= flowflow.get(each_var, set())

    return dataflow


def _dependencies(dataflow, out_vars, var):
    deps = set()
    # finds the dependencies of var
    for from_var, to_vars in dataflow.items():
        if var in to_vars:
            deps.add(from_var)
    return deps


def _times_shared(dataflow, var):
    return len(dataflow.get(var, set()))


class _MultiplySharedException(Exception):
    pass


def _singly_shared_paths(dataflow, in_vars, out_vars, var):
    expand_vars = set()

    for dep_var in _dependencies(dataflow, out_vars, var):
        if dep_var in in_vars:
            # dependence is input variable
            return {var}
        shared = _times_shared(dataflow, dep_var)
        if shared == 0:
            return set()
        if shared > 1:
            # dep_var is multiply shared, cannot form a singly path
            raise _MultiplySharedException
        # recursively find paths to dependent variables
        expand_vars |= _singly_shared_paths(
            dataflow, in_vars, out_vars, dep_var)

    expand_vars.add(var)
    return expand_vars


def _multiply_shared_paths(dataflow, in_vars, out_vars):
    # all variables
    vars = set(dataflow)
    for to_set in dataflow.values():
        vars |= to_set

    multiply_shared_vars = {
        var for var in vars if _times_shared(dataflow, var) > 1}

    paths = {}
    for var in multiply_shared_vars:
        try:
            paths[var] = _singly_shared_paths(dataflow, in_vars, out_vars, var)
        except _MultiplySharedException:
            pass
    return paths


def _dataflow_paths(dataflow, in_vars, out_vars):
    """
    Generates paths that are singly shared to be generated in one shot, but
    ordered with dependencies in mind, by separating multiply shared variables.
    """
    dataflow = copy.deepcopy(dataflow)
    paths = _multiply_shared_paths(dataflow, in_vars, out_vars)
    if not paths:
        paths = {}
        for var in out_vars:
            paths[var] = _singly_shared_paths(dataflow, in_vars, out_vars, var)
        yield paths
        return
    for var in paths:
        del dataflow[var]
    yield from _dataflow_paths(dataflow, in_vars, out_vars)
    yield paths


def _flatten_compositional_flow(flows):
    new_flows = []
    for f in flows:
        if isinstance(f, CompositionalFlow):
            new_flows += _flatten_compositional_flow(f.flows)
        else:
            new_flows.append(f)
    return new_flows


def _resolved_dependencies_generate(env, paths, next_paths, dataflow, in_vars):
    """
    Collects select expressions with same conditionals into the same if
    statement.

    If statement conditionals must be multiply shared for collection, so at
    this point here, it is safe to assume that same conditional will not get
    expanded, because otherwise it is not multiply shared and there is nothing
    left for collection.
    """
    def expand_expr(env, expand_vars, expr):
        if is_expression(expr):
            args = [expand_expr(env, expand_vars, a) for a in expr.args]
            return expression_factory(expr.op, *args)
        if is_variable(expr) or isinstance(expr, Label):
            if expr in in_vars:
                # do not expand if is an input variable
                return expr
            if expr not in expand_vars:
                # do not expand if not in expand_vars
                return expr
            # recursively expand expression
            return expand_expr(env, expand_vars, env[expr])
        if is_numeral(expr):
            return expr
        raise TypeError(
            'Do not know how to expand the expression {}'.format(expr))

    def label_to_var(expr):
        if isinstance(expr, Label):
            return Variable('imd_{}'.format(expr.label_value))
        if is_expression(expr):
            args = [label_to_var(a) for a in expr.args]
            return expression_factory(expr.op, *args)
        if is_variable(expr) or is_numeral(expr):
            return expr

    def filter(env, paths):
        unified_expand_vars = set()
        for each_vars in paths.values():
            unified_expand_vars |= each_vars

        return {var: expr for var, expr in env.items()
                if var in paths or var in unified_expand_vars}

    local_env = filter(env, paths)

    # finds if statement collections and normal assignments
    select_cond_map = {}
    assign_map = {}
    for var in paths:
        expr = local_env[var]
        if isinstance(expr, Label):
            # a terrible hack for output variables, because expr for out_vars
            # is always a label, if cann't get it then it is not our business
            # to generate it as it may be shared
            expr = local_env.get(expr, expr)
        if isinstance(expr, SelectExpr):
            true_expr, false_expr = expr.true_expr, expr.false_expr
            true_expr = expand_expr(local_env, paths[var], true_expr)
            false_expr = expand_expr(local_env, paths[var], false_expr)
            select_cond_list = select_cond_map.setdefault(expr.bool_expr, [])
            select_cond_list.append((var, true_expr, false_expr))
        else:
            assign_map[var] = expand_expr(local_env, paths[var], expr)

    # normal assignments
    flows = [AssignFlow(v, e) for v, e in assign_map.items()]

    # if statements
    for bool_expr, select_cond_list in select_cond_map.items():
        true_flow = CompositionalFlow()
        false_flow = CompositionalFlow()
        for var, true_expr, false_expr in select_cond_list:
            true_flow += AssignFlow(var, true_expr)
            false_flow += AssignFlow(var, false_expr)
            bool_expr = expand_expr(local_env, paths[var], bool_expr)
        flows.append(IfFlow(bool_expr, true_flow, false_flow))

    return CompositionalFlow(flows)


def generate(env, out_vars):
    dataflow = _dataflow_dictionary(env, out_vars)

    # input variables are those without others depending on them
    in_vars = {var for var in dataflow if is_variable(var)}

    # generate dependence paths
    paths_deps = list(_dataflow_paths(dataflow, in_vars, out_vars))

    if not paths_deps:
        return IdentityFlow()

    flows = []
    for index, paths in enumerate(paths_deps):
        try:
            next_paths = paths_deps[index]
        except IndexError:
            next_paths = {}
        # note that next_paths is modified
        flows.append(_resolved_dependencies_generate(
            env, paths, next_paths, dataflow, in_vars))

    return CompositionalFlow(_flatten_compositional_flow(reversed(flows)))
