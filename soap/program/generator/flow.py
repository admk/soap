import collections

from soap import logger
from soap.expression import (
    is_variable, is_expression, expression_factory,
    Variable, InputVariable, InputVariableTuple, OutputVariableTuple
)
from soap.program.flow import (
    AssignFlow, IfFlow, WhileFlow, CompositionalFlow,
    PragmaInputFlow, PragmaOutputFlow, ProgramFlow
)
from soap.program.graph import (
    DependenceGraph, HierarchicalDependenceGraph
)
from soap.semantics import (
    ErrorSemantics, FloatInterval, is_constant, is_numeral, Label
)


class CodeGenerator(object):
    def __init__(self, graph=None, env=None, out_vars=None, parent=None,
                 label_infix=None, in_var_infix=None, out_var_infix=None):
        super().__init__()
        if env:
            self.env = env
        if graph:
            self.graph = graph
        else:
            logger.info(
                'Partitioning dependency graph for {}'.format(
                    ', '.join(str(v) for v in out_vars)))
            self.graph = DependenceGraph(env, out_vars)
        if not env:
            self.env = self.graph.env
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
            if isinstance(expr, ErrorSemantics):
                expr = expr.v
            if isinstance(expr, FloatInterval):
                if not is_constant(expr):
                    logger.warning(
                        'Bound found as a constant, defaults to min val.')
                expr = expr.min
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

        return Variable(name, expr.dtype)

    def generate(self):
        if isinstance(self.graph, HierarchicalDependenceGraph):
            order = self.graph.local_order()
        else:
            order = [
                v for v in self.graph.dfs_postorder()
                if isinstance(v, Label) or isinstance(v, Variable)
                or isinstance(v, OutputVariableTuple)]
        logger.info('Generating code for nodes {}'.format(
            ','.join(str(o) for o in order)))
        flows = []
        for var in order:
            flows.append(self.emit_dispatcher(var, order))
        return CompositionalFlow(self._flatten(list(flows)))

    def emit_dispatcher(self, var, order):
        env = self.graph.env
        expr = env.get(var)
        if not expr:
            if isinstance(var, HierarchicalDependenceGraph):
                expr = var
        emit_func_name = 'emit_{}'.format(expr.__class__.__name__)
        emit = getattr(self, emit_func_name, self.generic_emit)
        return self._flatten(emit(var, expr, order))

    def generic_emit(self, var, expr, order):
        if isinstance(var, InputVariable):
            return
        if expr is None:
            raise ValueError(
                'Node {} has no expression, cannot generate.'.format(var))
        return AssignFlow(
            self._with_infix(var, self.out_var_infix),
            self._with_infix(expr, self.in_var_infix))

    def emit_HierarchicalDependenceGraph(self, var, expr, order):
        return self.__class__(
            var, parent=self.parent,
            label_infix=self.label_infix,
            in_var_infix=self.in_var_infix,
            out_var_infix=self.out_var_infix).generate()

    def emit_OutputVariableTuple(self, var, expr, order):
        return

    def emit_SelectExpr(self, var, expr, order):
        graph = self.graph
        if isinstance(graph, HierarchicalDependenceGraph):
            subgraphs = graph.subgraphs
        else:
            subgraphs = {}

        def generate_branch_output_interface(label):
            if not isinstance(var, OutputVariableTuple):
                return AssignFlow(
                    self._with_infix(var, self.out_var_infix),
                    self._with_infix(label, self.in_var_infix))
            flows = []
            for var_out, var_in in zip(var.args, label.args):
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
            if not isinstance(subgraph, HierarchicalDependenceGraph):
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
            expr = env.get(label)
            if is_variable(expr) or is_numeral(expr):
                return expr
            if expr is None:
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
        # find input variables for the loop
        init_vars = list(DependenceGraph(bool_env, [bool_label]).input_vars())
        init_vars += list(DependenceGraph(loop_state, loop_vars).input_vars())
        new_init_vars = []
        for var in init_vars:
            if var not in new_init_vars:
                # because these variables are labelled `InputVariable`
                # we need to re-label them
                new_init_vars.append(var)
        init_flow_generator = generator_class(
            env=init_state, out_vars=new_init_vars, parent=self,
            label_infix=infix, out_var_infix=infix)
        init_flow = init_flow_generator.generate()

        # while loop generation
        bool_expr = self._with_infix(bool_expr, infix)
        loop_flow_generator = generator_class(
            env=loop_state, out_vars=sorted(loop_state.keys(), key=str),
            parent=self, label_infix=infix, in_var_infix=infix,
            out_var_infix=infix)
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


def generate(meta_state, inputs, outputs):
    from soap.semantics import label
    _, env = label(meta_state, None, outputs)
    if not isinstance(inputs, collections.OrderedDict):
        raise TypeError('Inputs must be an OrderedDict.')
    input_flow = PragmaInputFlow(inputs)
    output_flow = PragmaOutputFlow(outputs)
    body_flow = CodeGenerator(env=env, out_vars=outputs).generate()
    flow = CompositionalFlow([input_flow, output_flow]) + body_flow
    return ProgramFlow(flow)
