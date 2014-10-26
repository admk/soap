from soap import logger
from soap.common import base_dispatcher
from soap.semantics.functions import arith_eval, bool_eval, fixpoint_eval


class BaseState(base_dispatcher('visit')):
    """Base state for all program states."""
    __slots__ = ()

    @classmethod
    def empty(cls):
        return cls(bottom=True)

    def generic_visit(self, flow):
        raise TypeError('No method to visit {!r}'.format(flow))

    def visit_IdentityFlow(self, flow):
        return self

    visit_InputFlow = visit_OutputFlow = visit_IdentityFlow

    def visit_AssignFlow(self, flow):
        return self[flow.var:arith_eval(flow.expr, self)]

    def visit_IfFlow(self, flow):
        bool_expr = flow.conditional_expr
        true_split, false_split = bool_eval(bool_expr, self)
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

    def transition(self, flow):
        return self.__call__(flow)
