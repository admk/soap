"""
.. module:: soap.program.flow
    :synopsis: Program flow graphs.
"""
from akpytemp import Template
from akpytemp.utils import code_gobble

from soap.common import base_dispatcher, superscript
from soap.semantics import BoxState, is_numeral, Label


def _code_gobble(s):
    return code_gobble(s).strip()


def _indent(code):
    return '\n'.join('    ' + c for c in code.split('\n')).rstrip() + '\n'


def _state_with_label(state, label):
    if state is None:
        return
    try:
        state = state.filter(lambda k: k.label == label)
        state = BoxState({k.variable: v for k, v in state.items()})
    except AttributeError:
        pass
    return str(state)


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

    def inputs(self):
        return input_output_variables(self)['inputs']

    def outputs(self):
        return input_output_variables(self)['outputs']

    def flow(self, state):
        """Evaluates the flow with state."""
        return state.transition(self)

    def debug(self, state=None):
        """Debug flow transitions at each step."""
        from soap.semantics.state import (
            IdentifierBaseState, IdentifierBoxState
        )
        state = state or self.inputs()
        if not isinstance(state, IdentifierBaseState):
            state = IdentifierBoxState(state or {})
        return self.format(self.flow(state))

    def format(self, state=None):
        raise NotImplementedError

    @property
    def label(self):
        return Label(id(self))

    def __eq__(self, other):
        return type(self) is type(other)

    def __str__(self):
        return self.format().replace('    ', '').replace('\n', '').strip()

    def __hash__(self):
        return hash(self.__class__)


class IdentityFlow(Flow):
    """Identity flow, does nothing."""
    def format(self, state=None):
        return 'skip; '

    def __bool__(self):
        return False

    def __repr__(self):
        return '{cls}()'.format(cls=self.__class__.__name__)


class InputFlow(IdentityFlow):
    def __init__(self, inputs):
        super().__init__()
        self.inputs = inputs

    def format(self, state=None):
        inputs = ', '.join(
            '{}: {}'.format(k, v) for k, v in self.inputs.items())
        return 'input ({}); '.format(inputs)

    def __repr__(self):
        return '{cls}({inputs!r})'.format(
            cls=self.__class__.__name__, inputs=self.inputs)


class OutputFlow(IdentityFlow):
    def __init__(self, outputs):
        super().__init__()
        self.outputs = outputs

    def format(self, state=None):
        outputs = ', '.join(str(v) for v in self.outputs)
        return 'output ({}); '.format(outputs)

    def __repr__(self):
        return '{cls}({outputs!r})'.format(
            cls=self.__class__.__name__, outputs=self.outputs)


class AssignFlow(Flow):
    """Assignment flow.

    Asks the state object to return a new state of assigning the variable with
    a value evaluated from the expression.
    """
    def __init__(self, var, expr):
        super().__init__()
        self.var = var
        self.expr = expr

    def format(self, state=None):
        s = '{var} := {expr}; '.format(var=self.var, expr=self.expr)
        if state:
            s += '\n' + _state_with_label(state, self.label)
        return s

    def __eq__(self, other):
        if not super().__eq__(other):
            return False
        return (self.var == other.var and self.expr == other.expr)

    def __repr__(self):
        return '{cls}(var={var!r}, expr={expr!r})'.format(
            cls=self.__class__.__name__, var=self.var, expr=self.expr)

    def __hash__(self):
        return hash((self.__class__, self.var, self.expr))


class IfFlow(Flow):
    """Program flow for conditional non-loop branching.  """
    def __init__(self, conditional_expr, true_flow, false_flow):
        super().__init__()
        self.conditional_expr = conditional_expr
        self.true_flow = true_flow
        self.false_flow = false_flow

    def format(self, state=None):
        render_kwargs = {
            'flow': self,
            'state': state,
            'label': superscript(self.label),
        }
        branch_template = Template(_code_gobble("""
            {% if state %}{# split_format #}
            {% end %}{# split_flow_format #}"""))

        formats = []
        zipper = [(self.true_flow,
                   self.label.attributed_true()),
                  (self.false_flow,
                   self.label.attributed_false())]
        for flow, label in zipper:
            split_format = _state_with_label(state, label)
            f = branch_template.render(
                render_kwargs, split_format=split_format,
                split_flow_format=flow.format(state))
            formats.append(_indent(f))
        true_format, false_format = formats

        if state:
            exit_label = self.label.attributed_exit()
            join_format = _state_with_label(state, exit_label)
        else:
            join_format = None

        template = Template(_code_gobble("""
            if ({# flow.conditional_expr #}) (
            {# true_format #}){% if flow.false_flow %} (
            {# false_format #}){% end %}; {% if state %}
            {# join_format #}{% end %}
            """))
        return template.render(
            render_kwargs, true_format=true_format, false_format=false_format,
            join_format=join_format)

    def __eq__(self, other):
        if not super().__eq__(other):
            return False
        return (self.conditional_expr == other.conditional_expr and
                self.true_flow == other.true_flow and
                self.false_flow == other.false_flow)

    def __repr__(self):
        return ('{cls}(conditional_expr={expr!r}, true_flow={true_flow!r}, '
                'false_flow={false_flow!r})').format(
            cls=self.__class__.__name__, expr=self.conditional_expr,
            true_flow=self.true_flow, false_flow=self.false_flow)

    def __hash__(self):
        return hash((self.__class__, self.conditional_expr,
                     self.true_flow, self.false_flow))


class WhileFlow(Flow):
    """Program flow for conditional while loops.

    Makes use of :class:`IfFlow` to define conditional branching. Computes the
    fixpoint of the state object iteratively."""
    def __init__(self, conditional_expr, loop_flow):
        super().__init__()
        self.conditional_expr = conditional_expr
        self.loop_flow = loop_flow

    def format(self, state=None):
        entry_label = self.label.attributed_entry()
        exit_label = self.label.attributed_exit()
        render_kwargs = {
            'flow': self,
            'state': state,
            'entry_format': _state_with_label(state, entry_label),
            'exit_format': _state_with_label(state, exit_label),
            'label': superscript(self.label),
        }
        loop_format = _indent(Template(_code_gobble("""
            {% if state %}{# entry_format #}
            {% end %}{# flow.loop_flow.format(state) #}
            """)).render(render_kwargs))
        template = Template(_code_gobble("""
            while ({# flow.conditional_expr #}) (
            {# loop_format #}); {% if state %}
            {# exit_format #}{% end %}"""))
        return template.render(render_kwargs, loop_format=loop_format)

    def __eq__(self, other):
        if not super().__eq__(other):
            return False
        return (self.conditional_expr == other.conditional_expr and
                self.loop_flow == other.loop_flow)

    def __repr__(self):
        return '{cls}(conditional_expr={expr!r}, loop_flow={flow!r})'.format(
            cls=self.__class__.__name__, expr=self.conditional_expr,
            flow=self.loop_flow)

    def __hash__(self):
        return hash((self.__class__, self.conditional_expr, self.loop_flow))


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

    def __add__(self, other):
        try:
            return CompositionalFlow(self.flows + other.flows)
        except AttributeError:
            return CompositionalFlow(self.flows + (other, ))

    def __bool__(self):
        return any(self.flows)

    def format(self, state=None):
        return '\n'.join(flow.format(state) for flow in self.flows)

    def __eq__(self, other):
        if not super().__eq__(other):
            return False
        return (self.flows == other.flows)

    def __repr__(self):
        return '{cls}(flows={flows!r})'.format(
            cls=self.__class__.__name__, flows=self.flows)

    def __hash__(self):
        return hash((self.__class__, self.flows))


class _VariableSetGenerator(base_dispatcher()):

    def generic_execute(self, flow, input, output):
        raise TypeError(
            'Do not know how to find variables in {!r}'.format(flow))

    def execute_IdentityFlow(self, flow, input, output):
        return set()

    execute_InputFlow = execute_OutputFlow = execute_IdentityFlow

    def execute_AssignFlow(self, flow, input, output):
        in_vars = out_vars = set()
        expr = flow.expr
        if input and not is_numeral(expr):
            in_vars = expr.vars()
        if output:
            out_vars = {flow.var}
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

    def _execute(self, flow, input=True, output=True):
        return super()._execute(flow, input, output)


flow_variables = _VariableSetGenerator()


class _InputOutputGenerator(base_dispatcher()):
    def __init__(self):
        super().__init__()
        self.inputs = self.outputs = None

    def execute_InputFlow(self, flow):
        self.inputs = flow.inputs

    def execute_OutputFlow(self, flow):
        self.outputs = flow.outputs

    def _execute_dont_care(self, flow):
        pass

    execute_IdentityFlow = execute_AssignFlow = _execute_dont_care

    def execute_IfFlow(self, flow):
        self(flow.true_flow)
        self(flow.false_flow)

    def execute_WhileFlow(self, flow):
        self(flow.loop_flow)

    def execute_CompositionalFlow(self, flow):
        for f in flow.flows:
            self(f)

    def __eq__(self, other):
        return NotImplemented


def input_output_variables(flow):
    g = _InputOutputGenerator()
    g(flow)
    rv = {
        'inputs': g.inputs,
        'outputs': g.outputs,
    }
    return rv
