"""
.. module:: soap.program.flow
    :synopsis: Program flow graphs.
"""
from akpytemp import Template
from akpytemp.utils import code_gobble as _code_gobble

from soap import logger
from soap.common import Label
from soap.semantics import Interval


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
    def __init__(self, label=None):
        self.label = label or Label()

    def flow(self, state):
        return self.transition(state, None)

    def debug(self, state):
        env = {}
        try:
            self.transition(state, env)
        except KeyboardInterrupt:
            logger.warning('KeyboardInterrupt')
        return color('{}\n'.format(state)) + self.format(env)

    def format(self, env=None):
        raise NotImplementedError

    def _env_update(self, env, state=None, true_state=None, false_state=None):
        def set(k, v):
            if v is None:
                return
            if k in env:
                env[k] |= v
            else:
                env[k] = v
        if env is None:
            return
        set((self.label, None), state)
        set((self.label, True), true_state)
        set((self.label, False), false_state)

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
    def format(self, env=None):
        s = 'skip; '
        if env is not None:
            s += '\n{state}'.format(state=self._env_get(env)[None])
        return s

    def transition(self, state, env):
        self._env_update(env, state)
        return state

    def __bool__(self):
        return False

    def __repr__(self):
        return '%s()' % self.__class__.__name__


class AssignFlow(Flow):
    """Assignment flow.

    Asks the state object to return a new state of assigning the variable with
    a value evaluated from the expression.
    """
    def __init__(self, var, expr, label=None):
        super().__init__(label=label)
        self.var = var
        self.expr = expr

    def transition(self, state, env):
        state = state.assign(self.var, self.expr)
        self._env_update(env, state)
        return state

    def format(self, env=None):
        s = str(self.var) + ' ≔ ' + str(self.expr) + '; '
        if env is not None:
            s += '\n{state}'.format(state=color(self._env_get(env)[None]))
        return s

    def __repr__(self):
        return '%s(%r, %r)' % (self.__class__.__name__, self.var, self.expr)

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
        super().__init__(label=label)
        self.conditional_expr = conditional_expr
        self.true_flow = true_flow
        self.false_flow = false_flow

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
            if {# flow.conditional_expr #} (
            {# true_format #}){% if flow.false_flow %} (
            {# false_format #});{% end %}{% if env %}
            {# color(flow._env_get(env)[None]) #}{% end %}
            """))
        return template.render(
            render_kwargs, true_format=true_format, false_format=false_format)

    def __repr__(self):
        return '{name}({expr!r}, {true_flow!r}, {false_flow!r})'.format(
            name=self.__class__.__name__, expr=self.conditional_expr,
            true_flow=self.true_flow, false_flow=self.false_flow)

    def __hash__(self):
        return hash((self.__class__.__name__, self.conditional_expr,
                     self.true_flow, self.false_flow))


class WhileFlow(SplitFlow):
    """Program flow for conditional while loops.

    Makes use of :class:`IfFlow` to define conditional branching. Computes the
    fixpoint of the state object iteratively."""
    def __init__(self, conditional_expr, loop_flow, label=None):
        super().__init__(label=label)
        self.conditional_expr = conditional_expr
        self.loop_flow = loop_flow

    def transition(self, state, env):
        prev_state = false_state = state.__class__(bottom=True)
        while state != prev_state:
            prev_state = state
            true_split, false_split = self._split(state)
            false_state |= false_split
            state = self.loop_flow.transition(true_split, env)
            self._env_update(env, state, true_split, false_split)
        return false_state

    def format(self, env=None):
        render_kwargs = dict(flow=self, env=env, color=color)
        loop_format = _indent(Template(code_gobble("""
            {% if env %}{# color(flow._env_get(env)[True]) #}
            {% end %}{# flow.loop_flow.format(env) #}
            """)).render(render_kwargs))
        rendered = Template(code_gobble("""
            while {# flow.conditional_expr #} (
            {# loop_format #});{% if env %}
            {# color(flow._env_get(env)[False]) #}{% end %}
            """)).render(render_kwargs, loop_format=loop_format)
        return rendered

    def __repr__(self):
        return '%s(%r, %r)' % (
            self.__class__.__name__, self.conditional_expr, self.loop_flow)

    def __hash__(self):
        return hash((
            self.__class__.__name__, self.conditional_expr, self.loop_flow))


class CompositionalFlow(Flow):
    """Flow for program composition.

    Combines multiple flow objects into a unified flow.
    """
    def __init__(self, flows=None, label=None):
        super().__init__(label=label)
        self.flows = tuple(flows or [])

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
        return any(bool(flow) for flow in self.flows)

    def format(self, env=None):
        return '\n'.join(flow.format(env) for flow in self.flows)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.flows)

    def __hash__(self):
        return hash((self.__class__.__name__, self.flows))
