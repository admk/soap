from soap import logger
from soap.common import base_dispatcher
from soap.semantics.functions import arith_eval, bool_eval, fixpoint_eval
from soap.program.flow import CompositionalFlow, WhileFlow


class BaseState(base_dispatcher('visit')):
    """Base state for all program states."""
    __slots__ = ()

    @classmethod
    def empty(cls):
        return cls(bottom=True)

    def generic_visit(self, flow):
        raise TypeError('No method to visit {!r}'.format(flow))

    def visit_SkipFlow(self, flow):
        return self

    visit_InputFlow = visit_OutputFlow = visit_SkipFlow

    def visit_AssignFlow(self, flow):
        return self.immu_update(flow.var, arith_eval(flow.expr, self))

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

    def visit_ForFlow(self, flow):
        state = self.transition(flow.init_flow)
        loop_flows = flow.loop_flow
        if isinstance(loop_flows, CompositionalFlow):
            loop_flows = loop_flows.flows
        else:
            loop_flows = [loop_flows]
        loop_flow = CompositionalFlow(loop_flows + [flow.incr_flow])
        while_flow = WhileFlow(flow.conditional_expr, loop_flow)
        return state.transition(while_flow)

    def visit_CompositionalFlow(self, flow):
        """Follows compositionality."""
        state = self
        for f in flow.flows:
            state = state.transition(f)
        return state

    def visit_ProgramFlow(self, flow):
        return self.transition(flow.body_flow)

    def is_fixpoint(self, other):
        """Fixpoint test, defaults to equality."""
        return self == other

    def widen(self, other):
        """Widening, defaults to least upper bound (i.e. join)."""
        return self | other

    def transition(self, flow):
        return self.__call__(flow)

    def update(self, key, value):
        raise AttributeError('Immutable object has no "update" method.')

    def immu_update(self, key, value):
        """
        Generate a new copy of this MetaState, and update the content with a
        new pair `key`: `value`.
        """
        new_mapping = dict(self)
        new_mapping[self._cast_key(key)] = self._cast_value(key, value)
        return self.__class__(new_mapping)
