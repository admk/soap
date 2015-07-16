"""
.. module:: soap.program.flow
    :synopsis: Program flow graphs.
"""
from collections import OrderedDict

from soap.common import base_dispatcher, indent
from soap.expression import AccessExpr, Variable
from soap.semantics import is_numeral


class Flow(object):
    """Program flow.

    It must define a member function :member:`flow`, which takes a state and
    returns a new state based on the data and control flows, as well as the
    *effect* of the computation associated with the flow, which is specified in
    the definition of the state.
    """
    def __init__(self):
        super().__init__()
        self._label = None

    def vars(self, input=True, output=True):
        return flow_variables(self, input, output)

    def flow(self, state):
        """Evaluates the flow with state."""
        return state.transition(self)

    def format(self):
        raise NotImplementedError('Override this method')

    def __add__(self, other):
        return CompositionalFlow(
            getattr(self, 'flows', (self, )) +
            getattr(other, 'flows', (other, )))

    def __eq__(self, other):
        raise NotImplementedError('Override this method')

    def __str__(self):
        return self.format().replace('    ', '').replace('\n', '').strip()


class SkipFlow(Flow):
    """Skip flow, does nothing."""
    def format(self):
        return 'skip; '

    def __bool__(self):
        return False

    def __repr__(self):
        return '{cls}()'.format(cls=self.__class__.__name__)

    def __eq__(self, other):
        return type(self) is type(other)

    def __hash__(self):
        return hash('skip;')


class AssignFlow(Flow):
    """Assignment flow.

    Asks the state object to return a new state of assigning the variable with
    a value evaluated from the expression.
    """
    def __init__(self, var, expr):
        super().__init__()
        self.var = var
        self.expr = expr

    def format(self):
        return '{var} = {expr}; '.format(var=self.var, expr=self.expr)

    def __repr__(self):
        return '{cls}(var={var!r}, expr={expr!r})'.format(
            cls=self.__class__.__name__, var=self.var, expr=self.expr)

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return (self.var == other.var and self.expr == other.expr)

    def __hash__(self):
        return hash((self.var, self.expr))


class IfFlow(Flow):
    """Program flow for conditional non-loop branching.  """
    def __init__(self, conditional_expr, true_flow, false_flow=None):
        super().__init__()
        self.conditional_expr = conditional_expr
        self.true_flow = true_flow
        self.false_flow = false_flow or SkipFlow()

    def format(self):
        template = 'if ({conditional_expr}) {{\n{true_format}}} '
        if self.false_flow:
            template += 'else {{\n{false_format}}} '
        return template.format(
            conditional_expr=self.conditional_expr,
            true_format=indent(self.true_flow.format()),
            false_format=indent(self.false_flow.format()))

    def __repr__(self):
        return ('{cls}(conditional_expr={expr!r}, true_flow={true_flow!r}, '
                'false_flow={false_flow!r})').format(
            cls=self.__class__.__name__, expr=self.conditional_expr,
            true_flow=self.true_flow, false_flow=self.false_flow)

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return (self.conditional_expr == other.conditional_expr and
                self.true_flow == other.true_flow and
                self.false_flow == other.false_flow)

    def __hash__(self):
        return hash((self.conditional_expr,
                     self.true_flow, self.false_flow))


class WhileFlow(Flow):
    """Program flow for conditional while loops.  """

    def __init__(self, conditional_expr, loop_flow):
        super().__init__()
        self.conditional_expr = conditional_expr
        self.loop_flow = loop_flow

    def format(self):
        loop_format = indent(self.loop_flow.format())
        template = 'while ({conditional_expr}) {{\n{loop_format}}} '
        return template.format(
            conditional_expr=self.conditional_expr, loop_format=loop_format)

    def __repr__(self):
        return '{cls}(conditional_expr={expr!r}, loop_flow={flow!r})'.format(
            cls=self.__class__.__name__, expr=self.conditional_expr,
            flow=self.loop_flow)

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return (self.conditional_expr == other.conditional_expr and
                self.loop_flow == other.loop_flow)

    def __hash__(self):
        return hash((self.conditional_expr, self.loop_flow))


class ForFlow(Flow):
    """Flow for for-loop.  """

    def __init__(self, init_flow, conditional_expr, incr_flow, loop_flow):
        super().__init__()
        self.init_flow = init_flow
        self.conditional_expr = conditional_expr
        self.incr_flow = incr_flow
        self.loop_flow = loop_flow

    def format(self):
        loop_format = indent(self.loop_flow.format())
        template = ('for ({init_flow} {conditional_expr}; {incr_flow}) '
                    '{{\n{loop_format}}} ')
        return template.format(
            init_flow=self.init_flow, conditional_expr=self.conditional_expr,
            incr_flow=str(self.incr_flow)[:-1], loop_format=loop_format)

    def __repr__(self):
        repr_str = (
            '{cls}(init_flow={init_flow!r}, conditional_expr={expr!r}, '
            'incr_flow={incr_flow!r}, loop_flow={flow!r})')
        return repr_str.format(
            cls=self.__class__.__name__, init_flow=self.init_flow,
            expr=self.conditional_expr, incr_flow=self.incr_flow,
            flow=self.loop_flow)

    def __hash__(self):
        return hash((
            self.init_flow, self.conditional_expr,
            self.incr_flow, self.loop_flow))

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return (self.init_flow == other.init_flow and
                self.conditional_expr == other.conditional_expr and
                self.incr_flow == other.incr_flow and
                self.loop_flow == other.loop_flow)


class CompositionalFlow(Flow):
    """Flow for program composition.

    Combines multiple flow objects into a unified flow.
    """
    def __init__(self, flows=None):
        super().__init__()
        new_flows = []
        for flow in (flows or []):
            if isinstance(flow, CompositionalFlow):
                new_flows += flow.flows
            else:
                new_flows.append(flow)
        self.flows = tuple(new_flows)

    def transition(self, state):
        for flow in self.flows:
            state = flow.transition(state)
        return state

    def __bool__(self):
        return any(self.flows)

    def format(self):
        return '\n'.join(flow.format() for flow in self.flows)

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return self.flows == other.flows

    def __repr__(self):
        return '{cls}(flows={flows!r})'.format(
            cls=self.__class__.__name__, flows=self.flows)

    def __hash__(self):
        return hash(self.flows)


pragma_keyword = '#pragma soap'


class PragmaFlow(Flow):
    pass


class PragmaInputFlow(PragmaFlow):
    def __init__(self, inputs):
        super().__init__()
        self.inputs = OrderedDict(inputs)

    def format(self):
        inputs = ', '.join('{dtype} {name} = {value}'.format(
            dtype=var.dtype, name=var.name, value=value)
            for var, value in self.inputs.items())
        return '{} input {} '.format(pragma_keyword, inputs)

    def __repr__(self):
        return '{cls}({inputs!r})'.format(
            cls=self.__class__.__name__, inputs=self.inputs)

    def __hash__(self):
        return hash(self.inputs)

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return self.inputs == other.inputs


class PragmaOutputFlow(PragmaFlow):
    def __init__(self, outputs):
        super().__init__()
        self.outputs = tuple(outputs)

    def format(self):
        outputs = ', '.join(str(v) for v in self.outputs)
        return '{} output {} '.format(pragma_keyword, outputs)

    def __repr__(self):
        return '{cls}({outputs!r})'.format(
            cls=self.__class__.__name__, outputs=self.outputs)

    def __hash__(self):
        return hash(self.outputs)

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return all(
            a.name == b.name for a, b in zip(self.outputs, other.outputs))


class ProgramFlow(Flow):
    def __init__(self, flow, decl=None):
        super().__init__()
        self.input_flows, self.output_flows, body_flows = \
            self._find_pragmas(flow)
        self.body_flow = CompositionalFlow(body_flows)
        self.original_flow = flow
        self.decl = decl or self._find_declarations(self.body_flow)

    def _find_declarations(self, flow):
        var_set = flow_variables(flow, input=True, output=True)
        return {
            var.name: var.dtype for var in var_set if var not in self.inputs}

    def _find_pragmas(self, flow):
        input_flows = []
        output_flows = []
        body_flows = []
        for each_flow in flow.flows:
            if isinstance(each_flow, PragmaInputFlow):
                input_flows.append(each_flow)
            elif isinstance(each_flow, PragmaOutputFlow):
                output_flows.append(each_flow)
            else:
                body_flows.append(each_flow)
        return input_flows, output_flows, body_flows

    @property
    def inputs(self):
        inputs = []
        for flow in self.input_flows:
            inputs += flow.inputs.items()
        return OrderedDict(inputs)

    @property
    def outputs(self):
        outputs = []
        for flow in self.output_flows:
            outputs += flow.outputs
        typed_outputs = []
        for var in outputs:
            if not var.dtype:
                name = var.name
                var = Variable(name, self.decl[name])
            typed_outputs.append(var)
        return typed_outputs

    def _format_declarations(self):
        decl_text = []
        for var, dtype in self.decl.items():
            decl_text.append('{} {};'.format(dtype, var))
        return '\n'.join(decl_text)

    def format(self):
        preamble = CompositionalFlow(self.input_flows + self.output_flows)
        text = preamble.format() + '\n' + self._format_declarations()
        return text + '\n' + self.body_flow.format()

    def __repr__(self):
        return '{cls}({flow!r})'.format(
            cls=self.__class__.__name__, flow=self.original_flow)

    def __hash__(self):
        return hash((self.__class__, self.original_flow))

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return (self.inputs == other.inputs and
                self.outputs == other.outputs and
                self.body_flow == other.body_flow)


class _VariableSetGenerator(base_dispatcher()):

    def generic_execute(self, flow, input, output):
        raise TypeError(
            'Do not know how to find variables in {!r}'.format(flow))

    def execute_SkipFlow(self, flow, input, output):
        return set()

    execute_ReturnFlow = execute_SkipFlow

    def execute_AssignFlow(self, flow, input, output):
        in_vars = out_vars = set()
        var, expr = flow.var, flow.expr
        if input and not is_numeral(expr):
            in_vars = expr.vars()
            if isinstance(var, AccessExpr):
                in_vars |= var.subscript.vars()
        if output:
            out_var = var
            if isinstance(var, AccessExpr):
                out_var = var.var
            out_vars = {out_var}
        return in_vars | out_vars

    def execute_IfFlow(self, flow, input, output):
        if input:
            in_vars = flow.conditional_expr.vars()
        else:
            in_vars = set()
        flow_vars = self(flow.true_flow, input, output)
        flow_vars |= self(flow.false_flow, input, output)
        return in_vars | flow_vars

    def execute_WhileFlow(self, flow, input, output):
        if input:
            in_vars = flow.conditional_expr.vars()
        else:
            in_vars = set()
        flow_vars = self(flow.loop_flow, input, output)
        return in_vars | flow_vars

    def execute_ForFlow(self, flow, input, output):
        if input:
            in_vars = flow.conditional_expr.vars()
        else:
            in_vars = set()
        flow_vars = self(flow.init_flow, input, output)
        flow_vars |= self(flow.loop_flow, input, output)
        flow_vars |= self(flow.incr_flow, input, output)
        return in_vars | flow_vars

    def execute_CompositionalFlow(self, flow, input, output):
        var_set = set()
        for f in flow.flows:
            var_set |= self(f, input, output)
        return var_set

    def execute_ProgramFlow(self, flow, input, output):
        var_set = set()
        if input:
            var_set |= set(flow.inputs)
        if output:
            var_set |= set(flow.outputs)
        return var_set

    def _execute(self, flow, input=True, output=True):
        return super()._execute(flow, input, output)


flow_variables = _VariableSetGenerator()
