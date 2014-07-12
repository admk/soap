import collections

from soap import logger
from soap.expression import (
    is_variable, is_expression, expression_factory,
    Variable, InputVariableTuple, OutputVariableTuple
)
from soap.program.flow import AssignFlow, IfFlow, WhileFlow, CompositionalFlow
from soap.program.graph import HierarchicalDependencyGraph, sorted_vars, unique
from soap.semantics import Label, is_numeral


class CodeGenerator(object):
    def __init__(self, graph=None, env=None, out_vars=None, parent=None,
                 label_infix=None, in_var_infix=None, out_var_infix=None):
        super().__init__()
        self.graph = graph or HierarchicalDependencyGraph(env, out_vars)
        self.parent = parent
        self.label_infix = label_infix
        self.in_var_infix = in_var_infix
        self.out_var_infix = out_var_infix

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

    def _with_infix(self, expr, var_infix, label_infix='__magic__'):
        if is_expression(expr):
            args = tuple(self._with_infix(a, var_infix, label_infix)
                         for a in expr.args)
            return expression_factory(expr.op, *args)
        if is_numeral(expr):
            return expr

        if isinstance(expr, Label):
            name = '_t{}'.format(expr.label_value)
            if label_infix == '__magic__':
                infix = self.label_infix
            else:
                infix = label_infix
        elif is_variable(expr):
            name = expr.name
            infix = var_infix
        else:
            raise TypeError(
                'Do not know how to add infix for {!r}'.format(expr))

        if not isinstance(infix, Label):
            if isinstance(infix, collections.Sequence):
                infix = '_'.join(str(i) for i in infix)

        if infix is not None:
            name = '{}_{}'.format(name, infix)

        return Variable(name)

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
        return AssignFlow(
            self._with_infix(var, self.out_var_infix),
            self._with_infix(expr, self.in_var_infix))

    def emit_HierarchicalDependencyGraph(self, var, expr, order):
        return self.__class__(
            var, parent=self.parent,
            label_infix=self.label_infix,
            in_var_infix=self.in_var_infix,
            out_var_infix=self.out_var_infix).generate()

    def emit_OutputVariableTuple(self, var, expr, order):
        return

    def emit_SelectExpr(self, var, expr, order):
        graph = self.graph
        subgraphs = graph.subgraphs

        def generate_branch_output_interface(label):
            if not isinstance(var, OutputVariableTuple):
                return AssignFlow(
                    self._with_infix(var, self.out_var_infix),
                    self._with_infix(label, self.in_var_infix))
            flows = []
            for var_out, var_in in zip(var, label):
                var_out = self._with_infix(var_out, self.out_var_infix)
                var_in = self._with_infix(var_in, self.in_var_infix)
                flows.append(AssignFlow(var_out, var_in))
            return CompositionalFlow(flows)

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
            generator = self.__class__(
                subgraph, parent=self.parent,
                label_infix=self.label_infix,
                in_var_infix=self.in_var_infix,
                out_var_infix=self.out_var_infix)
            flows = generator.generate()
            del order[order.index(subgraph)]
            return flows

        def generate_branch(label):
            flow = generate_branch_locals(label)
            flow += generate_branch_output_interface(label)
            return flow

        bool_expr = self._with_infix(expr.bool_expr, self.in_var_infix)
        true_flow = generate_branch(expr.true_expr)
        false_flow = generate_branch(expr.false_expr)
        return IfFlow(bool_expr, true_flow, false_flow)

    def emit_External(self, var, expr, order):
        return AssignFlow(
            self._with_infix(var, var_infix=self.out_var_infix),
            self._with_infix(
                expr.var, var_infix=self.parent.out_var_infix,
                label_infix=self.parent.label_infix))

    def emit_FixExpr(self, var, expr, order):
        def expand_simple_expression(env, label):
            if is_numeral(label):
                return label
            expr = env[label]
            if is_variable(expr) or is_numeral(expr):
                return expr
            if expr.is_bottom():
                return label
            args = [expand_simple_expression(env, l) for l in expr.args]
            return expression_factory(expr.op, *args)

        def var_to_list(v):
            if isinstance(v, OutputVariableTuple):
                return list(v)
            return [v]

        out_vars = var_to_list(var)
        infix = out_vars
        generator_class = self.__class__

        bool_label, bool_env = expr.bool_expr
        bool_expr = expand_simple_expression(bool_env, bool_label)
        loop_state = expr.loop_state
        loop_vars = var_to_list(expr.loop_var)
        init_state = expr.init_state

        # things to be generated before loop
        init_vars = sorted_vars(bool_env, bool_label)
        init_vars += sorted_vars(loop_state, loop_vars)
        init_vars = unique(init_vars)
        init_flow_generator = generator_class(
            env=init_state, out_vars=init_vars, parent=self,
            label_infix=infix, out_var_infix=infix)
        init_flow = init_flow_generator.generate()

        # while loop generation
        bool_expr = self._with_infix(bool_expr, infix)
        loop_flow_generator = generator_class(
            env=loop_state, out_vars=loop_vars, parent=self,
            label_infix=infix, in_var_infix=infix, out_var_infix=infix)
        loop_flow = loop_flow_generator.generate()
        loop_flow = WhileFlow(bool_expr, loop_flow)

        # loop_vars interface
        exit_flow = CompositionalFlow()
        for out_var, loop_var in zip(out_vars, loop_vars):
            exit_flow += AssignFlow(
                self._with_infix(out_var, self.out_var_infix),
                self._with_infix(loop_var, infix))

        flows = [init_flow, loop_flow, exit_flow]
        return flows


def generate(env, out_vars):
    return CodeGenerator(env=env, out_vars=out_vars).generate()


def meta_state_to_flow(meta_state, out_vars):
    from soap.semantics import BoxState, label
    _, env = label(meta_state, BoxState(bottom=True), out_vars)
    return generate(env, out_vars)
