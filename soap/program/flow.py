"""
.. module:: soap.program.flow
    :synopsis: Program flow graphs.
"""
from collections import OrderedDict

from soap.common import base_dispatcher, indent
from soap.expression.linalg import AccessExpr
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
    def __init__(self, conditional_expr, true_flow, false_flow):
        super().__init__()
        self.conditional_expr = conditional_expr
        self.true_flow = true_flow
        self.false_flow = false_flow

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
        template = ('for ({init_flow}; {conditional_expr}; {incr_flow}) '
                    '{{\n{loop_format}}} ')
        return template.format(
            init_flow=self.init_flow, conditional_expr=self.conditional_expr,
            incr_flow=self.incr_flow, loop_format=loop_format)

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
        self.flows = tuple(flows or [])

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
        return (self.flows == other.flows)

    def __repr__(self):
        return '{cls}(flows={flows!r})'.format(
            cls=self.__class__.__name__, flows=self.flows)

    def __hash__(self):
        return hash(self.flows)


class FunctionFlow(Flow):
    def __init__(self, name, inputs, flow):
        super().__init__()
        self.name = name
        self.inputs = OrderedDict(inputs)
        *body_flow, return_flow = flow.flows
        self.body_flow = CompositionalFlow(body_flow)
        if not isinstance(return_flow, ReturnFlow):
            raise ValueError('Function must return a value.')
        self.return_flow = return_flow

    @property
    def outputs(self):
        return self.return_flow.outputs

    def format(self):
        inputs = ', '.join('{dtype} {name}: {value}'.format(
            dtype=var.dtype, name=var.name, value=value)
            for var, value in self.inputs.items())
        flow = indent(self.body_flow.format())
        return 'def {name}({inputs}) {{\n{flow}}} '.format(
            name=self.name, inputs=inputs, flow=flow)

    def __repr__(self):
        return '{cls}({name!r}, {inputs!r}, {flow!r})'.format(
            cls=self.__class__.__name__, name=self.name, inputs=self.inputs,
            flow=self.body_flow)

    def __hash__(self):
        return hash(
            (self.__class__, self.name,
             tuple(self.inputs.items()), self.body_flow))

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return (self.name == other.name and self.inputs == other.inputs and
                self.body_flow == other.body_flow)


class ReturnFlow(Flow):
    def __init__(self, outputs):
        super().__init__()
        self.outputs = tuple(outputs)

    def format(self):
        outputs = ', '.join(str(v) for v in self.outputs)
        return 'return {}; '.format(outputs)

    def __repr__(self):
        return '{cls}({outputs!r})'.format(
            cls=self.__class__.__name__, outputs=self.outputs)

    def __hash__(self):
        return hash(self.outputs)

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return self.outputs == other.outputs


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

    def execute_CompositionalFlow(self, flow, input, output):
        var_set = set()
        for f in flow.flows:
            var_set |= self(f, input, output)
        return var_set

    def execute_FunctionFlow(self, flow, input, output):
        var_set = set()
        if input:
            var_set |= set(flow.inputs)
        if output:
            var_set |= set(flow.outputs)
        return var_set

    def _execute(self, flow, input=True, output=True):
        return super()._execute(flow, input, output)


flow_variables = _VariableSetGenerator()
