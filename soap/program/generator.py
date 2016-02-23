import collections

from soap.common import indent
from soap import logger
from soap.datatype import ArrayType
from soap.expression import (
    is_variable, is_expression, expression_factory,
    Variable, InputVariable, InputVariableTuple, OutputVariableTuple,
    AccessExpr, UpdateExpr, Subscript, operators
)
from soap.program.flow import (
    AssignFlow, IfFlow, WhileFlow, CompositionalFlow,
    PragmaInputFlow, PragmaOutputFlow, ProgramFlow, _decl_str
)
from soap.program.graph import (
    DependenceGraph, HierarchicalDependenceGraph
)
from soap.semantics import (
    ErrorSemantics, FloatInterval, is_constant, is_numeral, Label
)
from soap.semantics.label import label_to_expr


class CodeGenerator(object):
    def __init__(self, graph=None, env=None, out_vars=None, parent=None,
                 label_infix=None, in_var_infix=None, out_var_infix=None):
        super().__init__()
        if env:
            self.env = env
        if graph:
            self.graph = graph
        else:
            logger.debug(
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

    def _with_infix(self, expr, var_infix, label_infix='__magic'):
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
            if label_infix == '__magic':
                infix = self.label_infix
            else:
                infix = label_infix
        elif is_variable(expr):
            name = expr.name
            infix = var_infix
        else:
            raise TypeError(
                'Do not know how to add infix for {!r}'.format(expr))
        dtype = expr.dtype

        if not isinstance(infix, Label):
            if isinstance(infix, collections.Sequence):
                infix = '_'.join(str(i) for i in infix)

        if infix is not None and not isinstance(dtype, ArrayType):
            name = '{}_{}'.format(name, infix)

        return Variable(name, dtype)

    def generate(self):
        if isinstance(self.graph, HierarchicalDependenceGraph):
            order = self.graph.local_order()
        else:
            order = [
                v for v in self.graph.dfs_preorder()
                if isinstance(v, Label) or isinstance(v, Variable)
                or isinstance(v, OutputVariableTuple)]
        logger.debug('Generating code for nodes {}'.format(
            ','.join(str(o) for o in order)))
        flows = []
        for var in order:
            flows.append(self._dispatcher(var, order))
        return CompositionalFlow(self._flatten(list(reversed(flows))))

    def _dispatcher(self, var, order):
        env = self.graph.env
        expr = env.get(var)
        if not expr:
            if isinstance(var, HierarchicalDependenceGraph):
                expr = var
        emit_func_name = 'emit_{}'.format(expr.__class__.__name__)
        emit = getattr(self, emit_func_name, self.generic_emit)
        return self._flatten(emit(var, expr, order))

    def _expand_simple_expression(self, env, label):
        if is_numeral(label):
            return label
        expr = env.get(label)
        if is_variable(expr) or is_numeral(expr):
            return expr
        if expr is None:
            return label
        args = [self._expand_simple_expression(env, l) for l in expr.args]
        return expression_factory(expr.op, *args)

    def generic_emit(self, var, expr, order):
        if isinstance(var, InputVariable):
            return
        if isinstance(var.dtype, ArrayType):
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

    def emit_BinaryBoolExpr(self, var, expr, order):
        return

    def emit_Subscript(self, var, expr, order):
        return

    def emit_AccessExpr(self, var, expr, order):
        access_var = self._with_infix(expr.var, self.in_var_infix)
        access_var = label_to_expr(var).true_var()
        subscript = Subscript(
            *(self._with_infix(index, self.in_var_infix)
              for index in self.env[expr.subscript]))
        return AssignFlow(
            self._with_infix(var, self.out_var_infix),
            AccessExpr(access_var, subscript))

    def emit_UpdateExpr(self, var, expr, order):
        _, subscript, update_expr = expr.args
        access_var = label_to_expr(var).true_var()
        subscript = Subscript(
            *(self._with_infix(index, self.in_var_infix)
              for index in self.env[subscript]))
        update_flow = AssignFlow(
            AccessExpr(access_var, subscript),
            self._with_infix(update_expr, self.in_var_infix))
        return update_flow

    def emit_SelectExpr(self, var, expr, order):
        graph = self.graph
        if isinstance(graph, HierarchicalDependenceGraph):
            subgraphs = graph.subgraphs
        else:
            subgraphs = {}

        def generate_branch_output_interface(label):
            if not isinstance(var, OutputVariableTuple):
                iterer = [(var, label)]
            else:
                iterer = zip(var.args, label.args)
            flows = []
            for var_out, var_in in iterer:
                if isinstance(var_out.dtype, ArrayType):
                    expr_in = self.env[var_in]
                    del order[order.index(var_in)]
                    if isinstance(expr_in, UpdateExpr):
                        _, subscript, update_expr = expr_in.args
                        access_var = label_to_expr(expr_in).true_var()
                        subscript = Subscript(
                            *(self._with_infix(index, self.in_var_infix)
                              for index in self.env[subscript]))
                        flow = AssignFlow(
                            AccessExpr(access_var, subscript),
                            self._with_infix(update_expr, self.in_var_infix))
                        flows.append(flow)
                    elif not is_variable(expr_in):
                        raise TypeError(
                            'Expect update to an array, not anything else.')
                else:
                    var_out = self._with_infix(var_out, self.out_var_infix)
                    var_in = self._with_infix(var_in, self.in_var_infix)
                    flows.append(AssignFlow(var_out, var_in))
            return CompositionalFlow(flows)

        def generate_branch_locals(label):
            if isinstance(label, InputVariableTuple):
                # there are no dependencies between each local label
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

        def generate_bool_expr(label):
            bool_expr = self.env[label]
            if is_numeral(bool_expr):
                return bool_expr
            if bool_expr.op not in operators.BOOLEAN_OPERATORS:
                return self._with_infix(label, var_infix=self.in_var_infix)
            bool_expr_args = (generate_bool_expr(a) for a in bool_expr.args)
            return expression_factory(bool_expr.op, *bool_expr_args)

        bool_expr = generate_bool_expr(expr.bool_expr)
        true_flow = generate_branch(expr.true_expr)
        false_flow = generate_branch(expr.false_expr)
        return IfFlow(bool_expr, true_flow, false_flow)

    def emit_External(self, var, expr, order):
        if isinstance(var.dtype, ArrayType):
            return
        return AssignFlow(
            self._with_infix(var, var_infix=self.out_var_infix),
            self._with_infix(
                expr.var, var_infix=self.parent.out_var_infix,
                label_infix=self.parent.label_infix))

    def emit_FixExpr(self, var, expr, order):
        def var_to_list(v):
            if isinstance(v, OutputVariableTuple):
                return list(v)
            return [v]

        out_vars = var_to_list(var)
        infix = out_vars
        generator_class = self.__class__

        bool_label, bool_env = expr.bool_expr
        bool_expr = self._expand_simple_expression(bool_env, bool_label)
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
                # we need to re-label them as Variable
                new_init_vars.append(Variable(var.name, var.dtype))
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
            if isinstance(out_var.dtype, ArrayType):
                continue
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


_template = """{rt_type} kernel_{func_name}({inout_list}) {{
{code}{rt_part}}}
"""


def generate_function(func_name, meta_state, inputs, outputs):
    flow = generate(meta_state, inputs, outputs)

    inout_list = list(inputs.keys())

    rt_val = []
    for output in outputs:
        if isinstance(output.dtype, ArrayType):
            if output not in inout_list:
                inout_list.append(output)
        else:
            rt_val.append(output)

    if len(rt_val) > 1:
        raise NotImplementedError('Can support only one return variable.')
    if rt_val:
        rt_val = rt_val.pop()
        rt_type = rt_val.dtype
        rt_part = '    return ' + rt_val.name + ';\n'
    else:
        rt_type = 'void'
        rt_part = ''

    inout_list = (
        _decl_str(var.name, var.dtype, shape=True) for var in inout_list)
    func_code = _template.format(
        rt_type=rt_type, func_name=func_name, inout_list=', '.join(inout_list),
        code=indent(flow.format()), rt_part=rt_part)
    return func_code
