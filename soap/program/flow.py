"""
.. module:: soap.program.flow
    :synopsis: Program flow graphs.
"""
def _indent(code):
    return '\n'.join('    ' + c for c in code.split('\n')).rstrip() + '\n'


class Flow(object):
    """Program flow.

    It must define a member function :member:`flow`, which takes a state and
    returns a new state based on the data and control flows, as well as the
    *effect* of the computation associated with the flow, which is specified in
    the definition of the state.
    """
    def flow(self, state):
        raise NotImplementedError

    def format(self):
        raise NotImplementedError

    def __str__(self):
        return self.format().replace('    ', '').replace('\n', '')


class IdentityFlow(Flow):
    """Identity flow, does nothing."""
    def flow(self, state):
        return state

    def format(self):
        return 'skip;'

    def debug(self, state):
        state = self.flow(state)
        return '%s\n%s' % (self.format(), state), state

    def __bool__(self):
        return False


class AssignFlow(Flow):
    """Assignment flow.

    Asks the state object to return a new state of assigning the variable with
    a value evaluated from the expression.
    """
    def __init__(self, var, expr):
        self.var = var
        self.expr = expr

    def flow(self, state):
        return state.assign(self.var, self.expr)

    def debug(self, state):
        state = self.flow(state)
        return '%s\n%s' % (self.format(), state), state

    def format(self):
        return str(self.var) + ' ≔ ' + str(self.expr) + ';'


class SplitFlow(Flow):
    def _split(self, state):
        return (state.conditional(self.conditional_expr, cond)
                for cond in (True, False))


class IfFlow(SplitFlow):
    """Program flow for conditional non-loop branching.

    Splits and joins the flow of the separate `True` and `False` branches.
    """
    def __init__(self, conditional_expr, true_flow, false_flow):
        self.conditional_expr = conditional_expr
        self.true_flow = true_flow
        self.false_flow = false_flow

    def flow(self, state):
        true_state, false_state = self._split(state)
        true_state = self.true_flow.flow(true_state)
        false_state = self.false_flow.flow(false_state)
        return true_state | false_state

    def debug(self, state=None):
        true_state, false_state = self._split(state)
        true_str, curr_true_state = self.true_flow.debug(true_state)
        false_str, curr_false_state = self.false_flow.debug(false_state)
        s = 'if %s (\n%s)' % \
            (self.conditional_expr, _indent(str(true_state) + '\n' + true_str))
        if self.false_flow:
            s += ' (\n%s)' % _indent(str(false_state) + '\n' + false_str)
        state = curr_true_state | curr_false_state
        return '%s;\n%s' % (s, state), state

    def format(self):
        s = 'if ' + str(self.conditional_expr) + ' (\n' + \
            _indent(self.true_flow.format()) + ')'
        if self.false_flow:
            s += ' (' + _indent(self.false_flow.format()) + ')'
        return s + ';'


class WhileFlow(SplitFlow):
    """Program flow for conditional while loops.

    Makes use of :class:`IfFlow` to define conditional branching. Computes the
    fixpoint of the state object iteratively."""
    def __init__(self, conditional_expr, loop_flow):
        self.conditional_expr = conditional_expr
        self.loop_flow = loop_flow

    def flow(self, state):
        fixpoint_flow = IfFlow(
            self.conditional_expr, self.loop_flow, IdentityFlow())
        prev_state = state.__class__(bottom=True)
        while state != prev_state:
            prev_state, state = state, fixpoint_flow.flow(state)
        return state.conditional(self.conditional_expr, False)

    def debug(self, state):
        prev_state = true_state = false_state = loop_state = \
            state.__class__(bottom=True)
        while state != prev_state:
            prev_state = state
            true_split, false_split = self._split(state)
            true_state |= true_split
            false_state |= false_split
            state = self.loop_flow.flow(true_split)
        true_string, _ = self.loop_flow.debug(true_state)
        true_string = _indent('%s\n%s' % (true_state, true_string))
        s = 'while %s (\n%s);\n%s' % \
            (self.conditional_expr, true_string, false_state)
        return s, false_state

    def __alt_flow(self, state):
        """An alternative approach to :member:`flow`."""
        branch = lambda state, cond: \
            state.conditional(self.conditional_expr, cond)
        prev_state = false_state = state.__class__(bottom=True)
        while state != prev_state:
            prev_state = state
            true_state = branch(state, True)
            false_state |= branch(state, False)
            state = self.loop_flow.flow(true_state)
        return false_state

    def format(self):
        return 'while ' + str(self.conditional_expr) + ' (\n' + \
            _indent(self.loop_flow.format()) + ');'


class CompositionalFlow(Flow):
    """Flow for program composition.

    Combines multiple flow objects into a unified flow.
    """
    def __init__(self, flows=None):
        self.flows = list(flows or [])

    def append(self, flow):
        self.flows.append(flow)

    def flow(self, state):
        for flow in self.flows:
            state = flow.flow(state)
        return state

    def debug(self, state=None):
        s = ''
        for flow in self.flows:
            string, state = flow.debug(state)
            s += string + '\n'
        return s, state

    def __add__(self, other):
        try:
            return CompositionalFlow(self.flows + other.flows)
        except AttributeError:
            return CompositionalFlow(self.flows + [other])

    def __bool__(self):
        return any(bool(flow) for flow in self.flows)

    def format(self):
        return '\n'.join(flow.format() for flow in self.flows)
