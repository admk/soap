"""
.. module:: soap.program.flow
    :synopsis: Program flow graphs.
"""
from akpytemp import Template
from akpytemp.utils import code_gobble

from soap import logger
from soap.context import context
from soap.label import Annotation, Iteration, Label, superscript
from soap.semantics.state import IdentifierBoxState


def _code_gobble(s):
    return code_gobble(s).strip()


def _color(s):
    return logger.color(str(s), l=logger.levels.debug)


def _indent(code):
    return '\n'.join('    ' + c for c in code.split('\n')).rstrip() + '\n'


def _state_with_label(state, label):
    return _color(state.filter(label=label))


class Flow(object):
    """Program flow.

    It must define a member function :member:`flow`, which takes a state and
    returns a new state based on the data and control flows, as well as the
    *effect* of the computation associated with the flow, which is specified in
    the definition of the state.
    """
    def __init__(self, iteration=None):
        super().__init__()
        self.iteration = iteration or Iteration(bottom=True)

    def flow(self, state=None):
        state = state or IdentifierBoxState()
        return self.transition(state)

    def debug(self, state=None):
        return self.format(self.flow(state))

    def format(self, state=None):
        raise NotImplementedError

    def transition(self, state):
        raise NotImplementedError

    @property
    def label(self):
        return Label(statement=self)

    @property
    def annotation(self):
        return Annotation(self.label, iteration=self.iteration)

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return self.iteration == other.iteration

    def __str__(self):
        return self.format().replace('    ', '').replace('\n', '')

    def __hash__(self):
        return hash((self.__class__, self.iteration))


class IdentityFlow(Flow):
    """Identity flow, does nothing."""
    def format(self, state=None):
        return '[skip]{annotation}; '.format(
            annotation=superscript(self.annotation))

    def transition(self, state):
        return state

    def __bool__(self):
        return False

    def __repr__(self):
        return '{cls}(iteration={iteration!r})'.format(
            cls=self.__class__.__name__, iteration=self.iteration)


class AssignFlow(Flow):
    """Assignment flow.

    Asks the state object to return a new state of assigning the variable with
    a value evaluated from the expression.
    """
    def __init__(self, var, expr, iteration=None):
        super().__init__(iteration=iteration)
        self.var = var
        self.expr = expr

    def transition(self, state):
        return state.assign(self.var, self.expr, self.annotation)

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
        return '{cls}(var={var!r}, expr={expr!r}, iteration={itr!r})'.format(
            cls=self.__class__.__name__,
            var=self.var, expr=self.expr, itr=self.iteration)

    def __hash__(self):
        return hash((self.__class__, self.var, self.expr, self.iteration))


class SplitJoinFlow(Flow):
    """A utility flow base class for control flow spliting and joining."""

    def _conditional_format(self, state, cond):
        return _state_with_label(
            state, self.annotation.label.attributed(cond))

    @property
    def conditional_variable(self):
        return self.conditional_expr.args[0]

    def _split_flow(self, state, true_flow, false_flow):
        true_split, false_split = state.pre_conditional(
            self.conditional_expr, self.annotation)
        true_state = true_flow.transition(true_split)
        false_state = false_flow.transition(false_split)
        return true_state, false_state

    def _join_flow(self, state, true_state, false_state):
        return state.post_conditional(
            self.conditional_expr, true_state, false_state, self.annotation)


class IfFlow(SplitJoinFlow):
    """Program flow for conditional non-loop branching.

    Splits and joins the flow of the separate `True` and `False` branches.
    """
    def __init__(self, conditional_expr, true_flow, false_flow,
                 iteration=None):
        super().__init__(iteration=iteration)
        self.conditional_expr = conditional_expr
        self.true_flow = true_flow
        self.false_flow = false_flow

    def transition(self, state):
        true_state, false_state = self._split_flow(
            state, self.true_flow, self.false_flow)
        return self._join_flow(state, true_state, false_state)

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
            if state:
                split_format = self._conditional_format(state, cond)
            else:
                split_format = None
            f = branch_template.render(
                render_kwargs, split_format=split_format,
                split_flow_format=flow.format(state))
            formats.append(_indent(f))
        true_format, false_format = formats

        if state:
            join_format = _state_with_label(state, self.label)
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
                'false_flow={false_flow!r}, iteration={iteration!r})').format(
            cls=self.__class__.__name__, expr=self.conditional_expr,
            true_flow=self.true_flow, false_flow=self.false_flow,
            iteration=self.iteration)

    def __hash__(self):
        return hash((self.__class__, self.conditional_expr,
                     self.true_flow, self.false_flow, self.iteration))


class WhileFlow(SplitJoinFlow):
    """Program flow for conditional while loops.

    Makes use of :class:`IfFlow` to define conditional branching. Computes the
    fixpoint of the state object iteratively."""
    def __init__(self, conditional_expr, loop_flow, iteration=None):
        super().__init__(iteration=iteration)
        self.conditional_expr = conditional_expr
        self.loop_flow = loop_flow

    def transition(self, state):
        check_itr = lambda itr, target_itr: (
            target_itr and itr % target_itr == 0)
        iter_count = 0
        prev_state = true_split = false_state = prev_join_state = \
            state.__class__(bottom=True)
        while True:
            try:
                iter_count += 1
                logger.persistent('Iteration', iter_count)
                # Fixpoint test
                curr_join_state = state | prev_join_state
                if check_itr(iter_count, context.unroll_factor):
                    # join all states in previous iterations
                    logger.persistent(
                        'No unroll', iter_count, l=logger.levels.info)
                    fixpoint = curr_join_state.is_fixpoint(prev_join_state)
                else:
                    fixpoint = state.is_fixpoint(prev_state)
                prev_state = state
                prev_join_state = curr_join_state
                if fixpoint:
                    break
                # Control and data flow
                true_split, false_split = self._split(state)
                false_state |= false_split
                state = self.loop_flow.transition(true_split)
                # Widening
                if check_itr(iter_count, context.widen_factor):
                    logger.persistent(
                        'Widening', iter_count, l=logger.levels.info)
                    state = prev_state.widen(state)
            except KeyboardInterrupt:
                break
        logger.unpersistent('Interation', 'No unroll', 'Widening')
        if not true_split.is_bottom():
            logger.warning(
                'While loop "{flow}" may never terminate with state '
                '{state}, analysis assumes it always terminates'
                .format(flow=self, state=true_split))
        return false_state

    def format(self, state=None):
        render_kwargs = {
            'flow': self,
            'state': state,
            'entry_format': self._conditional_format(state, True),
            'exit_format': self._conditional_format(state, False),
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
        return ('{cls}(conditional_expr={expr!r}, loop_flow={flow!r}, '
                'iteration={iteration!r})').format(
            cls=self.__class__.__name__,
            expr=self.conditional_expr, flow=self.loop_flow,
            iteration=self.iteration)

    def __hash__(self):
        return hash((
            self.__class__, self.conditional_expr, self.loop_flow,
            self.iteration))


class CompositionalFlow(Flow):
    """Flow for program composition.

    Combines multiple flow objects into a unified flow.
    """
    def __init__(self, flows=None, iteration=None):
        super().__init__(iteration=iteration)
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
        return '{cls}(flows={flows!r}, iteration={iteration!r})'.format(
            cls=self.__class__.__name__,
            flows=self.flows, iteration=self.iteration)

    def __hash__(self):
        return hash((self.__class__, self.flows, self.iteration))
