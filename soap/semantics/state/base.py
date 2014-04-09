from soap import logger
from soap.context import context
from soap.semantics.state.functions import arith_eval, bool_eval


class BaseState(object):
    """Base state for all program states."""
    __slots__ = ()

    def empty(self):
        return self.__class__(bottom=True)

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

    def _solve_fixpoint(self, flow):
        def _is_fixpoint(
                state, prev_state, curr_join_state, prev_join_state,
                iter_count):
            if context.unroll_factor:
                if iter_count % context.unroll_factor == 0:
                    # join all states in previous iterations
                    logger.info('No unroll', iter_count)
                    return curr_join_state.is_fixpoint(prev_join_state)
            return state.is_fixpoint(prev_state)

        def _widen(state, prev_state, iter_count):
            if context.unroll_factor:
                if iter_count % context.unroll_factor == 0:
                    logger.info('Widening', iter_count)
                    state = prev_state.widen(state)
            return state

        iter_count = 0
        loop_state = self
        entry_state = entry_join_state = exit_join_state = self.empty()
        prev_entry_state = prev_entry_join_state = self.empty()
        prev_loop_state = self.empty()

        while True:
            iter_count += 1
            logger.persistent('Iteration', iter_count)

            # Split state
            entry_state, exit_state = bool_eval(
                loop_state, flow.conditional_expr)
            exit_join_state |= exit_state

            # Fixpoint test
            entry_join_state = entry_state | prev_entry_join_state
            if _is_fixpoint(
                    entry_state, prev_entry_state,
                    entry_join_state, prev_entry_join_state,
                    iter_count):
                break

            # Update previous values
            prev_entry_state = entry_state
            prev_entry_join_state = entry_join_state
            prev_loop_state = loop_state

            # Loop flow
            loop_state = entry_state.transition(flow.loop_flow)

            # Widening
            loop_state = _widen(loop_state, prev_loop_state, iter_count)

        logger.unpersistent('Iteration')

        return {
            'entry': entry_join_state,
            'exit': exit_join_state,
            'last_entry': entry_state,
            'last_exit': loop_state,
        }

    def _warn_non_termination(self, flow):
        if self.is_bottom():
            return
        logger.warning(
            'While loop "{flow}" may never terminate with state {state}, '
            'analysis assumes it always terminates'.format(
                flow=flow, state=self))

    def visit_WhileFlow(self, flow):
        fixpoint = self._solve_fixpoint(flow)
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
