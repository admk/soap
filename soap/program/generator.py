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


class CodeGenerator(object):
    def __init__(self, graph=None, env=None, out_vars=None):
        super().__init__()
        self.graph = graph or HierarchicalDependencyGraph(env, out_vars)

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
            var, *order = order
            expr = env.get(var)
            if not expr:
                if isinstance(var, HierarchicalDependencyGraph):
                    expr = var
            emit_func_name = 'emit_{}'.format(expr.__class__.__name__)
            emit = getattr(self, emit_func_name, self.generic_emit)
            flows.append(emit(var, expr, order))
        return CompositionalFlow(self._flatten(flows))

    def emit_HierarchicalDependencyGraph(self, var, expr, order):
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
