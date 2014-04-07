"""
.. module:: soap.program.flow
    :synopsis: Program flow graphs.
"""
from akpytemp import Template
from akpytemp.utils import code_gobble

from soap import logger
from soap.label import Annotation, Label, superscript


def _code_gobble(s):
    return code_gobble(s).strip()


def _color(s):
    return logger.color(str(s), l=logger.levels.debug)


def _indent(code):
    return '\n'.join('    ' + c for c in code.split('\n')).rstrip() + '\n'


def _state_with_label(state, label):
    if state is None:
        return
    return _color(state.filter(label=label))


class Flow(object):
    """Program flow.

    It must define a member function :member:`flow`, which takes a state and
    returns a new state based on the data and control flows, as well as the
    *effect* of the computation associated with the flow, which is specified in
    the definition of the state.
    """
    def vars(self):
        if isinstance(self, IdentityFlow):
            return set()
        if isinstance(self, AssignFlow):
            return {self.var}
        if isinstance(self, IfFlow):
            return self.true_flow.vars() | self.false_flow.vars()
        if isinstance(self, WhileFlow):
            return self.loop_flow.vars()
        if isinstance(self, CompositionalFlow):
            vars = set()
            for f in self.flows:
                vars |= f.vars()
            return vars
        raise TypeError('Unrecognized self object {}'.format(self))

    def flow(self, state):
        return state.transition(self)

    def debug(self, state=None):
        from soap.semantics.state import (
            IdentifierBaseState, IdentifierBoxState
        )
        state = state or IdentifierBoxState()
        if not isinstance(state, IdentifierBaseState):
            raise TypeError('state object type is not IdentifierBaseState.')
        return self.format(self.flow(state))

    def format(self, state=None):
        raise NotImplementedError

    @property
    def label(self):
        return Label(statement=self)

    @property
    def annotation(self):
        return Annotation(self.label)

    def __eq__(self, other):
        return type(self) is type(other)

    def __str__(self):
        return self.format().replace('    ', '').replace('\n', '')

    def __hash__(self):
        return hash(self.__class__)


class IdentityFlow(Flow):
    """Identity flow, does nothing."""
    def format(self, state=None):
        return '[skip]{annotation}; '.format(
            annotation=superscript(self.annotation))

    def __bool__(self):
        return False

    def __repr__(self):
        return '{cls}()'.format(cls=self.__class__.__name__)


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
        s = '[{var} ≔ {expr}]{annotation}; '.format(
            var=self.var, expr=self.expr,
            annotation=superscript(self.annotation))
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
            'annotation': superscript(self.annotation),
        }
        branch_template = Template(_code_gobble("""
            {% if state %}{# split_format #}
            {% end %}{# split_flow_format #}"""))

        formats = []
        for flow, cond in (self.true_flow, True), (self.false_flow, False):
            if cond:
                label = flow.annotation.label.attributed_true()
            else:
                label = flow.annotation.label.attributed_false()
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
            if [{# flow.conditional_expr #}]{# annotation #} (
            {# true_format #}){% if flow.false_flow %} (
            {# false_format #});{% end %}{% if state %}
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
        entry_label = self.annotation.label.attributed_entry()
        exit_label = self.annotation.label.attributed_exit()
        render_kwargs = {
            'flow': self,
            'state': state,
            'entry_format': _state_with_label(state, entry_label),
            'exit_format': _state_with_label(state, exit_label),
            'annotation': superscript(self.annotation),
        }
        loop_format = _indent(Template(_code_gobble("""
            {% if state %}{# entry_format #}
            {% end %}{# flow.loop_flow.format(state) #}
            """)).render(render_kwargs))
        template = Template(_code_gobble("""
            while [{# flow.conditional_expr #}]{# annotation #} (
            {# loop_format #});{% if state %}
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
