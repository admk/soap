from soap import logger
from soap.semantics.state.functions import (
    arith_eval, bool_eval, to_meta_state, fixpoint_eval
)


class BaseState(object):
    """Base state for all program states."""
    __slots__ = ()

    @classmethod
    def empty(cls):
        return cls(bottom=True)

    def transition(self, flow):
        return getattr(self, 'visit_' + flow.__class__.__name__)(flow)

    def visit_IdentityFlow(self, flow):
        return self

    def visit_AssignFlow(self, flow):
        return self[flow.var:arith_eval(self, flow.expr)]

    def visit_IfFlow(self, flow):
        true_split, false_split = bool_eval(self, flow.conditional_expr)
        true_split = true_split.transition(flow.true_flow)
        false_split = false_split.transition(flow.false_flow)
        return true_split | false_split

    def _warn_non_termination(self, flow_or_meta_state):
        if self.is_bottom():
            return
        logger.warning(
            'Loop/fixpoint computation "{loop}" may never terminate with state'
            '{state}, analysis assumes it always terminates.'
            .format(loop=flow_or_meta_state, state=self))

    def visit_WhileFlow(self, flow):
        fixpoint = fixpoint_eval(
            self, flow.conditional_expr, loop_flow=flow.loop_flow)
        fixpoint['last_entry']._warn_non_termination(flow)
        return fixpoint['exit']

    def visit_CompositionalFlow(self, flow):
        """Follows compositionality."""
        state = self
        for f in flow.flows:
            state = state.transition(f)
        return state

    def is_fixpoint(self, other):
        """Fixpoint test, defaults to equality."""
        return self == other

    def widen(self, other):
        """Widening, defaults to least upper bound (i.e. join)."""
        return self | other
