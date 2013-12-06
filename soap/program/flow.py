"""
.. module:: soap.program.flow
    :synopsis: Program flow graphs.
"""
from reprlib import recursive_repr

from akpytemp import Template
from akpytemp.utils import code_gobble as _code_gobble

from soap import logger
from soap.common.label import FlowLabel, superscript
from soap.semantics.error import Interval
from soap.semantics.state import BoxState


code_gobble = lambda s: _code_gobble(s).strip()
color = lambda s: logger.color(str(s), l=logger.levels.debug)


def _indent(code):
    return '\n'.join('    ' + c for c in code.split('\n')).rstrip() + '\n'


class Flow(object):
    """Program flow.

    It must define a member function :member:`flow`, which takes a state and
    returns a new state based on the data and control flows, as well as the
    *effect* of the computation associated with the flow, which is specified in
    the definition of the state.
    """
    def _update_label(self, label):
        self.label = label or FlowLabel(self)

    def flow(self, state=None):
        state = state or BoxState()
        return self.transition(state, None)

    def flow_debug(self, state):
        env = {}
        curr_state = self.transition(state, env)
        return curr_state, color('{}\n'.format(state)) + self.format(env)

    def debug(self, state=None):
        state = state or BoxState()
        return self.flow_debug(state)[1]

    def format(self, env=None):
        raise NotImplementedError

    def _env_update(self, env, state=None, true_state=None, false_state=None):
        def update(k, v):
            if v is None:
                return
            if k in env:
                env[k] |= v
            else:
                env[k] = v
        if env is None:
            return
        update((self.label, None), state)
        update((self.label, True), true_state)
        update((self.label, False), false_state)

    def _env_get(self, env):
        def get(k, a):
            return env.get((k, a), Interval(bottom=True))
        return {
            None: get(self.label, None),
            True: get(self.label, True),
            False: get(self.label, False),
        }

    def transition(self, state, env):
        raise NotImplementedError

    def __str__(self):
        return self.format().replace('    ', '').replace('\n', '')

    def __hash__(self):
        return hash(self.__class__.__name__)


class IdentityFlow(Flow):
    """Identity flow, does nothing."""
    def __init__(self, label=None):
        super().__init__()
        self._update_label(label)

    def format(self, env=None):
        s = '[skip]{label}; '.format(label=superscript(self.label))
        if env is not None:
            s += '\n{state}'.format(state=self._env_get(env)[None])
        return s

    def transition(self, state, env):
        self._env_update(env, state)
        return state

    def __bool__(self):
        return False

    @recursive_repr()
    def __repr__(self):
        return '{cls}(label={label!r})'.format(
            cls=self.__class__.__name__, label=self.label)


class AssignFlow(Flow):
    """Assignment flow.

    Asks the state object to return a new state of assigning the variable with
    a value evaluated from the expression.
    """
    def __init__(self, var, expr, label=None):
        super().__init__()
        self.var = var
        self.expr = expr
        self._update_label(label)

    def transition(self, state, env):
        state = state.assign(self.var, self.expr, self.label)
        self._env_update(env, state)
        return state

    def format(self, env=None):
        s = '[{var} ≔ {expr}]{label}; '.format(
            var=self.var, expr=self.expr, label=superscript(self.label))
        if env is not None:
            s += '\n{state}'.format(state=color(self._env_get(env)[None]))
        return s

    @recursive_repr()
    def __repr__(self):
        return '{cls}(var={var!r}, expr={expr!r}, label={label!r})'.format(
            cls=self.__class__.__name__,
            var=self.var, expr=self.expr, label=self.label)

    def __hash__(self):
        return hash((self.__class__.__name__, self.var, self.expr))


class SplitFlow(Flow):
    def _split(self, state):
        return (state.conditional(self.conditional_expr, cond)
                for cond in (True, False))


class IfFlow(SplitFlow):
    """Program flow for conditional non-loop branching.

    Splits and joins the flow of the separate `True` and `False` branches.
    """
    def __init__(self, conditional_expr, true_flow, false_flow, label=None):
        super().__init__()
        self.conditional_expr = conditional_expr
        self.true_flow = true_flow
        self.false_flow = false_flow
        self._update_label(label)

    def transition(self, state, env):
        true_split, false_split = self._split(state)
        true_state = self.true_flow.transition(true_split, env)
        false_state = self.false_flow.transition(false_split, env)
        state = true_state | false_state
        self._env_update(env, state, true_split, false_split)
        return state

    def format(self, env=None):
        render_kwargs = dict(flow=self, env=env, color=color)
        true_template = Template(code_gobble("""
            {% if env %}{# color(flow._env_get(env)[True]) #}
            {% end %}{# flow.true_flow.format(env) #}
            """))
        true_format = _indent(true_template.render(render_kwargs))
        false_template = Template(code_gobble("""
            {% if env %}{# color(flow._env_get(env)[False]) #}
            {% end %}{# flow.false_flow.format(env) #}
            """))
        false_format = _indent(false_template.render(render_kwargs))
        template = Template(code_gobble("""
            if [{# flow.conditional_expr #}]{# label #} (
            {# true_format #}){% if flow.false_flow %} (
            {# false_format #});{% end %}{% if env %}
            {# color(flow._env_get(env)[None]) #}{% end %}
            """))
        return template.render(
            render_kwargs, label=superscript(self.label),
            true_format=true_format, false_format=false_format)

    @recursive_repr()
    def __repr__(self):
        return ('{cls}(conditional_expr={expr!r}, true_flow={true_flow!r}, '
                'false_flow={false_flow!r}, label={label!r})').format(
            cls=self.__class__.__name__, expr=self.conditional_expr,
            true_flow=self.true_flow, false_flow=self.false_flow,
            label=self.label)

    def __hash__(self):
        return hash((self.__class__.__name__, self.conditional_expr,
                     self.true_flow, self.false_flow))


class WhileFlow(SplitFlow):
    """Program flow for conditional while loops.

    Makes use of :class:`IfFlow` to define conditional branching. Computes the
    fixpoint of the state object iteratively."""
    def __init__(self, conditional_expr, loop_flow,
                 unroll_factor=50, widen_factor=100, label=None):
        super().__init__()
        self.unroll_factor = unroll_factor
        self.widen_factor = widen_factor
        self.conditional_expr = conditional_expr
        self.loop_flow = loop_flow
        self._update_label(label)

    def transition(self, state, env):
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
                if check_itr(iter_count, self.unroll_factor):
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
                state = self.loop_flow.transition(true_split, env)
                # Comes before widening to ensure preciseness?
                self._env_update(env, state, true_split, false_split)
                # Widening
                if check_itr(iter_count, self.widen_factor):
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
                ''.format(flow=self, state=true_split))
        return false_state

    def format(self, env=None):
        render_kwargs = dict(flow=self, env=env, color=color)
        loop_format = _indent(Template(code_gobble("""
            {% if env %}{# color(flow._env_get(env)[True]) #}
            {% end %}{# flow.loop_flow.format(env) #}
            """)).render(render_kwargs))
        template = Template(code_gobble("""
            while [{# flow.conditional_expr #}]{# label #} (
            {# loop_format #});{% if env %}
            {# color(flow._env_get(env)[False]) #}{% end %}
            """))
        rendered = template.render(
            render_kwargs, label=superscript(self.label),
            loop_format=loop_format)
        return rendered

    @recursive_repr()
    def __repr__(self):
        return ('{cls}(conditional_expr={expr!r}, loop_flow={flow!r}, '
                'label={label!r})').format(
            cls=self.__class__.__name__,
            conditional_expr=self.conditional_expr, flow=self.loop_flow,
            label=self.label)

    def __hash__(self):
        return hash((
            self.__class__.__name__, self.conditional_expr, self.loop_flow))


class CompositionalFlow(Flow):
    """Flow for program composition.

    Combines multiple flow objects into a unified flow.
    """
    def __init__(self, flows=None, label=None):
        super().__init__()
        self.flows = tuple(flows or [])
        self._update_label(label)

    def transition(self, state, env):
        for flow in self.flows:
            state = flow.transition(state, env)
        self._env_update(env, state)
        return state

    def __add__(self, other):
        try:
            return CompositionalFlow(self.flows + other.flows)
        except AttributeError:
            return CompositionalFlow(self.flows + (other, ))

    def __bool__(self):
        return any(self.flows)

    def format(self, env=None):
        return '\n'.join(flow.format(env) for flow in self.flows)

    @recursive_repr()
    def __repr__(self):
        return '{cls}(flows={flows!r})'.format(
            cls=self.__class__.__name__, flows=self.flows)

    def __hash__(self):
        return hash((self.__class__.__name__, self.flows))
