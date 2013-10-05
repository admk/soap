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
        return self.transition(state)[1]

    def debug(self, state):
        return self.transition(state)[0]

    def format(self):
        raise NotImplementedError

    def transition(self, state):
        raise NotImplementedError

    def __str__(self):
        return self.format().replace('    ', '').replace('\n', '')


class IdentityFlow(Flow):
    """Identity flow, does nothing."""
    def format(self):
        return 'skip;'

    def transition(self, state):
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

    def transition(self, state):
        state = state.assign(self.var, self.expr)
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
    def __init__(self, conditional_expr, truetransition, falsetransition):
        self.conditional_expr = conditional_expr
        self.truetransition = truetransition
        self.falsetransition = falsetransition

    def transition(self, state=None):
        true_state, false_state = self._split(state)
        true_str, curr_true_state = self.truetransition.transition(true_state)
        false_str, curr_false_state = self.falsetransition.transition(false_state)
        s = 'if %s (\n%s)' % \
            (self.conditional_expr, _indent(str(true_state) + '\n' + true_str))
        if self.falsetransition:
            s += ' (\n%s)' % _indent(str(false_state) + '\n' + false_str)
        state = curr_true_state | curr_false_state
        return '%s;\n%s' % (s, state), state

    def format(self):
        s = 'if ' + str(self.conditional_expr) + ' (\n' + \
            _indent(self.truetransition.format()) + ')'
        if self.falsetransition:
            s += ' (' + _indent(self.falsetransition.format()) + ')'
        return s + ';'


class WhileFlow(SplitFlow):
    """Program flow for conditional while loops.

    Makes use of :class:`IfFlow` to define conditional branching. Computes the
    fixpoint of the state object iteratively."""
    def __init__(self, conditional_expr, looptransition):
        self.conditional_expr = conditional_expr
        self.looptransition = looptransition

    def transition(self, state):
        prev_state = true_state = false_state = state.__class__(bottom=True)
        while state != prev_state:
            prev_state = state
            true_split, false_split = self._split(state)
            true_state |= true_split
            false_state |= false_split
            state = self.looptransition.flow(true_split)
        true_string, _ = self.looptransition.transition(true_state)
        true_string = _indent('%s\n%s' % (true_state, true_string))
        s = 'while %s (\n%s);\n%s' % \
            (self.conditional_expr, true_string, false_state)
        return s, false_state

    def __alttransition(self, state):
        """An alternative approach to :member:`flow`."""
        branch = lambda state, cond: \
            state.conditional(self.conditional_expr, cond)
        prev_state = false_state = state.__class__(bottom=True)
        while state != prev_state:
            prev_state = state
            true_state = branch(state, True)
            false_state |= branch(state, False)
            state = self.looptransition.flow(true_state)
        return false_state

    def format(self):
        return 'while ' + str(self.conditional_expr) + ' (\n' + \
            _indent(self.looptransition.format()) + ');'


class CompositionalFlow(Flow):
    """Flow for program composition.

    Combines multiple flow objects into a unified flow.
    """
    def __init__(self, flows=None):
        self.flows = list(flows or [])

    def append(self, flow):
        self.flows.append(flow)

    def transition(self, state=None):
        s = ''
        for flow in self.flows:
            string, state = flow.transition(state)
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
