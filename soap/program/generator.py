from pprint import pprint
import collections

from soap.expression import (
    is_variable, is_expression, expression_factory,
    Variable, InputVariableTuple, OutputVariableTuple,
    SelectExpr
)
from soap.label import Label
from soap.program.flow import (
    IdentityFlow, AssignFlow, IfFlow, CompositionalFlow
)
from soap.program.graph import (
    expression_dependencies, DependencyGraph, HierarchicalDependencyGraph,
    CyclicGraphException
)
from soap.semantics import is_numeral, MetaState


def branch_merge(env, out_vars):

    def sorted_args(expr, count_env=True):
        if not expr or is_variable(expr) or is_numeral(expr):
            return []
        if isinstance(expr, (Label, OutputVariableTuple)):
            return [expr]
        if isinstance(expr, InputVariableTuple):
            return list(expr.args)
        if is_expression(expr):
            args = []
            for a in expr.args:
                args += sorted_args(a, count_env)
            return args
        if isinstance(expr, MetaState):
            if not count_env:
                return []
            args = []
            for a in expr.values():
                args += sorted_args(a, count_env)
            return args
        raise TypeError('Do not know how to find args of {}'.format(expr))

    def merge(env, var):
        expr = env.get(var)
        dep_vars = sorted_args(expr, False)

        # not if-then-else
        if not isinstance(expr, SelectExpr):
            return env, dep_vars

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
        if not true_env:
            return env, dep_vars

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

        return new_env, dep_vars

    if not isinstance(out_vars, collections.Sequence):
        raise TypeError('Output variables out_vars must be a sequence.')

    for var in out_vars:
        new_env, dep_vars = merge(env, var)
        if env != new_env:
            try:
                DependencyGraph(new_env, out_vars)
            except CyclicGraphException:
                pass
            else:
                env = new_env
        # depth-first recursively merge branches
        env = branch_merge(env, dep_vars)

    return env


def _generate_unified(graph, out_vars):

    def generate_expression(graph, expr, prev_locals):
        """
        Generate expression by expanding it as far as possible, until some
        shared variables used some where else.
        """
        def next_vars_add(next_vars, new_next_vars):
            for n in new_next_vars:
                if n in next_vars:
                    continue
                next_vars.append(n)
            return next_vars

        if is_variable(expr) or is_numeral(expr):
            return expr, [], []

        if isinstance(expr, (Label, OutputVariableTuple)):
            expanded_expr = env[expr]

            # must look ahead for statement generation...
            if isinstance(expanded_expr, OutputVariableTuple):
                if beneath(None, expanded_expr) <= beneath_vars:
                    # multiply shared, but only used in the labels beneath it
                    stmt, next_vars = generate_statement(graph, expanded_expr)
                    return expr, [stmt], next_vars
                # multiply shared, also used somewhere else
                return expr, [], [expanded_expr]

            if isinstance(expanded_expr, SelectExpr):
                bool_expr = expanded_expr.bool_expr
                true_expr = expanded_expr.true_expr
                false_expr = expanded_expr.false_expr
                flows = []
                next_vars = []
                for br_expr in true_expr, false_expr:
                    bn_vars = beneath_vars | {br_expr}
                    br_expr, br_stmt, br_next_vars = \
                        generate_expression(graph, br_expr)

                    if isinstance(br_expr, tuple):
                        var_tup = expr
                        expr_tup = br_expr
                    else:
                        var_tup = [expr]
                        expr_tup = [br_expr]
                    flow = br_stmt
                    flow += [
                        AssignFlow(var, expr)
                        for var, expr in zip(var_tup, expr_tup)]
                    flow = CompositionalFlow(flow)

                    flows.append(flow)
                    next_vars = next_vars_add(next_vars, br_next_vars)

                true_flow, false_flow = flows

                bool_expr, bool_stmt, bool_next_vars = generate_expression(
                    env, dataflow_dict, bool_expr, beneath_vars | {bool_expr})
                next_vars = next_vars_add(next_vars, bool_next_vars)

                flow = bool_stmt
                flow.append(IfFlow(bool_expr, true_flow, false_flow))
                return expr, flow, next_vars

            if not graph.is_multiply_shared(expr):
                return generate_expression(graph, expanded_expr)
            # multiply shared, but only used locally
            if graph.locals(expr):
                return generate_expression(
                    env, dataflow_dict, expanded_expr, beneath_vars | {expr})
            # multiply shared, used globally
            return expr, [], [expr]

        if isinstance(expr, InputVariableTuple):
            # FIXME temporary hack
            expr_list = []
            next_vars = []
            stmt_list = []
            for arg in expr:
                arg_expr, stmt, arg_next_vars = generate_expression(
                    env, dataflow_dict, arg, beneath_vars | {arg})
                expr_list.append(arg_expr)
                next_vars = next_vars_add(next_vars, arg_next_vars)
                stmt_list += stmt
            return tuple(expr_list), stmt_list, next_vars

        if is_expression(expr):
            args = []
            next_vars = []
            stmt_list = []
            for arg in expr.args:
                arg, stmt, arg_vars = generate_expression(graph, arg)
                args.append(arg)
                next_vars = next_vars_add(next_vars, arg_vars)
                stmt_list += stmt
            return expression_factory(expr.op, *args), stmt_list, next_vars

        raise TypeError('Do not know how to expand {}'.format(expr))

    def remove_duplicates(l):
        n = []
        for e in l:
            if e in n:
                continue
            n.append(e)
        return n

    def generate_statement(graph, gen_var):
        # FIXME hack for output variables
        expr = graph.env.get(gen_var)
        if not expr:
            return [], []

        if isinstance(expr, Variable):
            expr = graph.env[expr]

        local_deps = graph.locals(gen_var)

        statements = []
        next_vars = []

        if isinstance(expr, SelectExpr):
            bool_statements, bool_next_vars = generate_statement(
                graph, expr.bool_expr)
            next_vars += bool_next_vars

            true_vars, false_vars = expr.true_expr, expr.false_expr
            both_statements = []
            for branch_vars in true_vars, false_vars:
                if not isinstance(branch_vars, collections.Sequence):
                    branch_vars = [branch_vars]
                branch_statements = []
                for v in branch_vars:
                    if v in local_deps:
                        statements, local_next_vars = generate_statement(
                            graph, v)
                    else:
                        statements, local_next_vars = [], [v]
                    branch_statements += statements
                    next_vars += local_next_vars
                both_statements.append(branch_statements)
            true_statements, false_statements = both_statements

            statements.append(bool_statements)
            statements.append(
                IfFlow(expr.bool_expr, true_statements, false_statements))

        if gen_var != expr:
            statements.append(AssignFlow(gen_var, expr))
            next_vars += expression_dependencies(expr)

        new_next_vars = []
        while next_vars:
            next_vars = graph.order_by_dependencies(
                remove_duplicates(next_vars))
            var, *next_vars = next_vars
            if var not in local_deps:
                new_next_vars.append(var)
            else:
                next_statements, next_next_vars = generate_statement(
                    graph, var)
                statements = next_statements + statements
                next_vars += next_next_vars

        return statements, new_next_vars

    def resolve_dataflow_order(graph, out_vars):
        out_vars_set = set(out_vars)
        gen_vars = []
        next_vars = []
        for var in out_vars:
            if graph.dataflows(var) & out_vars_set:
                # some variable to be generated depends on it,
                # generate it later
                next_vars.append(var)
            else:
                gen_vars.append(var)
        return gen_vars, next_vars

    gen_vars, next_vars = resolve_dataflow_order(graph, out_vars)

    statements = []
    for var in gen_vars:
        statement, nvars = generate_statement(graph, var)
        statements.append(statement)
        for v in nvars:
            if v not in next_vars and v not in gen_vars:
                next_vars.append(v)

    if next_vars:
        next_statements = generate_unified(graph, next_vars)
        statements = next_statements + statements
    return statements


def generate_graph(graph):
    if not graph:
        return []
    next_vars = graph.out_vars
    while next_vars:
        var, *next_vars = graph.order_by_dependencies(next_vars)
        generate_graph(graph.subgraph(var))


class CodeGenerator(object):
    def __init__(self, graph=None, env=None, out_vars=None):
        super().__init__()
        self.graph = graph or HierarchicalDependencyGraph(env, out_vars)
        pprint(self.graph.edges)

    def _flatten(self, flows):
        if flows is None:
            return []
        if not isinstance(flows, collections.Sequence):
            return [flows]
        if isinstance(flows, CompositionalFlow):
            flows = flows.flows

        new_flows = []
        for f in flows:
            new_flows += self._flatten(f)

        return new_flows

    def generate(self):
        order = self.graph.local_order()
        env = self.graph.env
        flows = []
        while order:
            var = order.pop()
            expr = env.get(var)
            if not expr:
                if isinstance(var, HierarchicalDependencyGraph):
                    expr = var
            emit_func_name = 'emit_{}'.format(expr.__class__.__name__)
            emit = getattr(self, emit_func_name, self.generic_emit)
            flows.append(emit(var, expr, order))
        return CompositionalFlow(self._flatten(flows))

    def emit_HierarchicalDependencyGraph(self, var, expr, order):
        return
        return self.__class__(var).generate()

    @staticmethod
    def generic_emit(var, expr, order):
        if not expr:
            if isinstance(var, InputVariableTuple):
                return
            raise ValueError(
                'Node {} has no expression, cannot generate.'.format(var))
        return AssignFlow(var, expr)


def generate(env, out_vars):
    return CodeGenerator(env, out_vars).generate()
