import collections

from soap import logger
from soap.expression import InputVariableTuple, OutputVariableTuple
from soap.program.flow import AssignFlow, IfFlow, CompositionalFlow
from soap.program.graph import HierarchicalDependencyGraph


class CodeGenerator(object):
    def __init__(self, graph=None, env=None, out_vars=None):
        super().__init__()
        self.graph = graph or HierarchicalDependencyGraph(env, out_vars)
        import pprint; pprint.pprint(self.graph.edges)

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
        flows = []
        while order:
            var = order.pop()
            flows.append(self.emit_dispatcher(var, order))
        return CompositionalFlow(self._flatten(list(reversed(flows))))

    def emit_dispatcher(self, var, order):
        env = self.graph.env
        expr = env.get(var)
        if not expr:
            if isinstance(var, HierarchicalDependencyGraph):
                expr = var
        logger.debug('Generating var: {!r}, expr: {!r}'.format(var, expr))
        emit_func_name = 'emit_{}'.format(expr.__class__.__name__)
        emit = getattr(self, emit_func_name, self.generic_emit)
        return self._flatten(emit(var, expr, order))

    def generic_emit(self, var, expr, order):
        if expr is None:
            if var == self.graph.out_var:
                if isinstance(var, InputVariableTuple):
                    return
            raise ValueError(
                'Node {} has no expression, cannot generate.'.format(var))
        return AssignFlow(var, expr)

    def emit_HierarchicalDependencyGraph(self, var, expr, order):
        return self.__class__(var).generate()

    def emit_OutputVariableTuple(self, var, expr, order):
        return

    def emit_SelectExpr(self, var, expr, order):
        graph = self.graph
        subgraphs = graph.subgraphs

        def generate_branch_output_interface(label):
            if not isinstance(var, OutputVariableTuple):
                return AssignFlow(var, label)
            return CompositionalFlow(
                AssignFlow(var_in, var_out)
                for var_in, var_out in zip(var, label))

        def generate_branch_locals(label):
            if isinstance(label, InputVariableTuple):
                # it can be proved there are no dependencies between each local
                # label
                flows = CompositionalFlow()
                for each in label:
                    flows += generate_branch_locals(each)
                return flows
            subgraph = subgraphs.get(label, label)
            if not isinstance(subgraph, HierarchicalDependencyGraph):
                return CompositionalFlow()
            if graph.is_multiply_shared(subgraph):
                # subgraph is not only used by this branch, so don't generate
                # the subgraph
                return CompositionalFlow()
            flows = self.__class__(subgraph).generate()
            del order[order.index(subgraph)]
            return flows

        def generate_branch(label):
            flow = generate_branch_locals(label)
            flow += generate_branch_output_interface(label)
            return flow

        true_flow = generate_branch(expr.true_expr)
        false_flow = generate_branch(expr.false_expr)
        return IfFlow(expr.bool_expr, true_flow, false_flow)


def generate(env, out_vars):
    return CodeGenerator(env=env, out_vars=out_vars).generate()
