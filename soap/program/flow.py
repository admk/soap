"""
.. module:: soap.program.flow
    :synopsis: Program flow graphs.
"""


class Flow(object):
    """Program flow."""
    def flow(self, state):
        raise NotImplementedError


class IdentityFlow(Flow):
    def flow(self, state):
        return state


class AssignFlow(Flow):
    """Assignment flow."""
    def __init__(self, var, expr):
        self.var = var
        self.expr = expr

    def flow(self, state):
        return state.assign(self.var, self.expr)

    def __str__(self):
        return str(self.var) + ' := ' + str(self.expr)


class IfFlow(Flow):
    """Program flow for conditional non-loop branching."""
    def __init__(self, conditional_expr, true_flow, false_flow):
        self.conditional_expr = conditional_expr
        self.true_flow = true_flow
        self.false_flow = false_flow

    def flow(self, state):
        true_state, false_state = [
            flow.flow(state.conditional(self.conditional_expr, cond))
            for flow, cond in [(self.true_flow, True),
                               (self.false_flow, False)]]
        return true_state.join(false_state)

    def __str__(self):
        return 'if ' + str(self.conditional_expr) + ' (' + \
            str(self.true_flow) + ') (' + str(self.false_flow) + ')'


class WhileFlow(Flow):
    """Program flow for conditional non-loop branching."""
    def __init__(self, conditional_expr, loop_flow):
        self.conditional_expr = conditional_expr
        self.loop_flow = loop_flow

    def flow(self, state):
        fixpoint_flow = IfFlow(
            self.conditional_expr, self.loop_flow, IdentityFlow())
        prev_state = state.bottom()
        state = state.copy()
        while state != prev_state:
            prev_state, state = state, fixpoint_flow.flow(state)
        return state.copy().conditional(self.conditional_expr, False)

    def __str__(self):
        return 'while ' + str(self.conditional_expr) + ' (' + \
            str(self.loop_flow) + ')'


class CompositionalFlow(Flow):
    """Flow for program composition."""
    def __init__(self, flows=None):
        self.flows = list(flows or [])

    def append_flow(self, flow):
        self.flows.append(flow)

    def flow(self, state):
        for flow in self.flows:
            state = flow.flow(state)
        return state

    def __add__(self, other):
        try:
            return CompositionalFlow(self.flows + other.flows)
        except AttributeError:
            return CompositionalFlow(self.flows + [other])

    def __str__(self):
        return '; '.join(str(flow) for flow in self.flows)
