import copy

from soap import logger
from soap.context import context
from soap.semantics.state.functions import arith_eval, bool_eval


class BaseState(object):
    """Base state for all program states."""
    __slots__ = ()

    def copy(self):
        return copy.deepcopy(self)

    def arith_eval(self, expr):
        return arith_eval(self, expr)

    def bool_eval(self, expr):
        def conditional(cond):
            var, cstr = bool_eval(self, expr, cond)
            state = self.copy()
            state[var] = cstr
            return state
        return [conditional(True), conditional(False)]

    def transition(self, flow):
        return getattr(self, 'visit_' + flow.__class__.__name__)(flow)

    def visit_IdentityFlow(self, flow):
        return self

    def visit_AssignFlow(self, flow):
        state = self.copy()
        state[flow.var] = state.arith_eval(flow.expr)
        return state

    def visit_IfFlow(self, flow):
        true_state, false_state = self.bool_eval(flow.conditional_expr)
        true_state = true_state.transition(flow.true_flow)
        false_state = false_state.transition(flow.false_flow)
        return true_state | false_state

    def _is_fixpoint(
            self, state, prev_state, curr_join_state, prev_join_state,
            iter_count):
        if context.unroll_factor and iter_count % context.unroll_factor == 0:
            # join all states in previous iterations
            logger.info('No unroll', iter_count)
            return curr_join_state.is_fixpoint(prev_join_state)
        return state.is_fixpoint(prev_state)

    def _widen(self, state, prev_state, iter_count):
        if context.unroll_factor and iter_count % context.unroll_factor == 0:
            logger.info('Widening', iter_count)
            state = prev_state.widen(state)
        return state

    def visit_WhileFlow(self, flow):
        iter_count = 0
        state = self
        prev_state = true_split = false_state = prev_join_state = \
            state.__class__(bottom=True)
        while True:
            iter_count += 1
            logger.persistent('Iteration', iter_count)
            # Fixpoint test
            curr_join_state = state | prev_join_state
            fixpoint = self._is_fixpoint(
                state, prev_state, curr_join_state, prev_join_state,
                iter_count)
            if fixpoint:
                break
            prev_state = state
            prev_join_state = curr_join_state
            # Control and data flow
            true_split, false_split = self.bool_eval(flow.conditional_expr)
            false_state |= false_split
            state = true_split.transition(flow.loop_flow)
            # Widening
            state = self._widen(state, prev_state, iter_count)
        logger.unpersistent('Interation')
        if not true_split.is_bottom():
            logger.warning(
                'While loop "{flow}" may never terminate with state '
                '{state}, analysis assumes it always terminates'
                .format(flow=self, state=true_split))
        return false_state

    def visit_CompositionalFlow(self, flow):
        """Compositionality.  """
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
