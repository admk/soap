import collections

from soap.expression import (
    is_variable, is_expression, expression_factory,
    Variable, SelectExpr, StateGetterExpr, BranchMetaExpr
)
from soap.label import Label
from soap.program.flow import (
    IdentityFlow, AssignFlow, IfFlow, CompositionalFlow
)
from soap.semantics import is_numeral, MetaState


def dataflow(env, vars):
    """Extract dataflow from env.  """

    def expression_dependencies(expr):
        # find dependent variables for the corresponding expression
        if not expr:
            # can't find expression for var or var is an input variable, so
            # there are no dependencies for it
            return set()
        if isinstance(expr, StateGetterExpr):
            raise NotImplementedError(
                'TODO special treatment for this, because of the labelling '
                'behaviour.')
        if is_expression(expr):
            # dependent variables in the expression
            return expr.vars()
        if isinstance(expr, Label) or is_variable(expr) or is_numeral(expr):
            # is a label/variable/constant, dependency is itself
            return {expr}
        raise TypeError(
            'Do not know how to find dependencies in expression {!r}'
            .format(expr))

    flow_dict = {}

    for var in vars:
        expr = env.get(var)
        expr_deps = expression_dependencies(expr)

        # each dependency assigns the data flow direction to var
        for dep_var in expr_deps:
            dep_flow = flow_dict.setdefault(dep_var, set())
            dep_flow.add(var)

        # finds the flow_dict of dependent variables, except input variables
        expr_deps = {var for var in expr_deps if not is_variable(var)}
        flowflow_dict = dataflow(env, expr_deps)

        # merge update dep_deps into deps
        for each_var in set(flow_dict) | set(flowflow_dict):
            each_flow = flow_dict.setdefault(each_var, set())
            each_flow |= flowflow_dict.get(each_var, set())

    return flow_dict


def beneath(dataflow_dict, var):
    beneath_set = set()
    to_vars = dataflow_dict.get(var, set())
    for to_var in to_vars:
        if is_variable(to_var):
            # is output variable, do nothing
            continue
        beneath_set |= beneath(dataflow_dict, to_var)
    return beneath_set | to_vars


def flatten_compositional_flow(flows):
    new_flows = []
    for f in flows:
        if isinstance(f, CompositionalFlow):
            new_flows += flatten_compositional_flow(f.flows)
        else:
            new_flows.append(f)
    return new_flows


def branch_merge(env, out_vars, label_context):

    def sorted_args(expr, count_env=True):
        if not expr or is_variable(expr) or is_numeral(expr):
            return []
        if isinstance(expr, Label):
            return [expr]
        if is_expression(expr):
            if isinstance(expr, StateGetterExpr):
                return [expr.meta_state]
            args = []
            for a in expr.args:
                args += sorted_args(a, count_env)
            return args
        if isinstance(expr, dict):
            if not count_env:
                return []
            args = []
            for a in expr.values():
                args += sorted_args(a, count_env)
            return args
        raise TypeError('Do not know how to find args of {}'.format(expr))

    def is_acyclic(env):
        class CyclicGraphException(Exception):
            pass

        def walk(env, var, found_vars):
            expr = env.get(var)
            for dep_var in sorted_args(expr):
                if dep_var in found_vars:
                    raise CyclicGraphException
                walk(env, dep_var, found_vars | {var})

        try:
            for var in env:
                walk(env, var, set())
        except CyclicGraphException:
            return False
        return True

    def merge(env, var, label_context):
        expr = env.get(var)
        dep_vars = sorted_args(expr, False)

        # not if-then-else
        if not isinstance(expr, SelectExpr):
            return env, dep_vars

        # discover things to collect
        bool_expr = expr.bool_expr
        true_env = {}
        false_env = {}
        for each_var, each_expr in env.items():
            if not isinstance(each_expr, SelectExpr):
                continue
            if each_expr.bool_expr != bool_expr:
                continue
            # same bool_expr, merge together
            true_env[each_var] = each_expr.true_expr
            false_env[each_var] = each_expr.false_expr

        # did not generate collection
        if not true_env:
            return env, dep_vars

        new_env = dict(env)

        # branch expression labelling
        true_label = label_context.Label(MetaState(true_env))
        false_label = label_context.Label(MetaState(false_env))
        branch_expr = BranchMetaExpr(bool_expr, true_label, false_label)
        branch_expr_label = label_context.Label(branch_expr)
        new_env[true_label] = true_env
        new_env[false_label] = false_env
        new_env[branch_expr_label] = branch_expr

        # collected variables labelling
        for each_var in true_env:
            new_env[each_var] = StateGetterExpr(branch_expr_label, each_var)

        return new_env, dep_vars

    if not isinstance(out_vars, collections.Sequence):
        raise TypeError('Output variables out_vars must be a sequence.')

    for var in out_vars:
        new_env, dep_vars = merge(env, var, label_context)
        if is_acyclic(new_env):
            env = new_env
        # depth-first recursively merge branches
        env = branch_merge(env, dep_vars, label_context)

    return env


def generate_unified(env, dataflow_dict, out_vars, beneath_vars=None):

    def getter_expr_label(state_label, var):
        return Variable('__imd_{}_{}'.format(state_label, var))

    def generate_expression(env, dataflow_dict, expr, beneath_vars=None):
        """
        Generate expression by expanding it as far as possible, until some
        shared variables used some where else.
        """
        if is_variable(expr) or is_numeral(expr):
            return expr, []

        beneath_vars = beneath_vars or set()

        if isinstance(expr, Label):
            to_vars_len = len(dataflow_dict[expr])
            if to_vars_len == 0:
                raise ValueError('Label is not used anywhere')
            if to_vars_len == 1:
                return generate_expression(
                    env, dataflow_dict, env[expr], beneath_vars | {expr})
            # to_vars_len > 1
            if beneath(dataflow_dict, expr) <= beneath_vars:
                # multiply shared, but only used in the labels beneath it
                return generate_expression(
                    env, dataflow_dict, env[expr], beneath_vars | {expr})
            return expr, [expr]

        if isinstance(expr, StateGetterExpr):
            state_label, var = expr.meta_state, expr.key
            return getter_expr_label(state_label, var), [state_label]

        if is_expression(expr):
            args = []
            next_vars = []
            for arg in expr.args:
                arg, arg_vars = generate_expression(
                    env, dataflow_dict, arg, beneath_vars | {arg})
                args.append(arg)
                next_vars += arg_vars
            return expression_factory(expr.op, *args), next_vars

        raise TypeError('Do not know how to expand {}'.format(expr))

    def generate_statement(env, dataflow_dict, gen_var):
        expr = env[gen_var]
        if is_variable(gen_var) or isinstance(gen_var, Label):
            expr_gen_var = expr
        else:
            expr_gen_var = gen_var
        if isinstance(expr, BranchMetaExpr):
            ...
            return
        expr, next_vars = generate_expression(env, dataflow_dict, expr_gen_var)
        return AssignFlow(gen_var, expr), next_vars

    def resolve_dataflow_order(dataflow_dict, out_vars):
        gen_vars = []
        next_vars = []
        for var in out_vars:
            beneath_vars = beneath(dataflow_dict, var)
            if beneath_vars and any(v in beneath_vars for v in gen_vars):
                # some variable to be generated depends on it,
                # generate it later
                next_vars.append(var)
            else:
                gen_vars.append(var)
        return gen_vars, next_vars

    gen_vars, next_vars = resolve_dataflow_order(dataflow_dict, out_vars)
    beneath_vars = beneath_vars or set()

    statements = []
    for var in gen_vars:
        if var in beneath_vars:
            continue
        statement, nvars = generate_statement(env, dataflow_dict, var)
        statements.append(statement)
        for v in nvars:
            if v not in next_vars:
                next_vars.append(v)

    if next_vars:
        next_statements = generate_unified(
            env, dataflow_dict, next_vars, beneath_vars | set(gen_vars))
        statements = next_statements + statements
    return statements


def generate(env, out_vars):
    dataflow_dict = dataflow(env, out_vars)
    statements = generate_unified(env, dataflow_dict, out_vars)
    return CompositionalFlow(flatten_compositional_flow(statements))
