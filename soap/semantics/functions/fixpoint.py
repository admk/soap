from soap import logger
from soap.context import context
from soap.common.cache import cached
from soap.semantics.functions.boolean import bool_eval
from soap.semantics.functions.meta import arith_eval_meta_state


def _is_fixpoint(state, prev_state, curr_join_state, prev_join_state,
                 iteration):
    if context.unroll_factor:
        if iteration % context.unroll_factor == 0:
            # join all states in previous iterations
            logger.info('No unroll', iteration)
            return curr_join_state.is_fixpoint(prev_join_state)
    return state.is_fixpoint(prev_state)


def _widen(state, prev_state, iteration):
    if context.unroll_factor:
        if iteration % context.unroll_factor == 0:
            logger.info('Widening', iteration)
            state = prev_state.widen(state)
    return state


@cached
def fixpoint_eval(state, bool_expr, loop_meta_state=None, loop_flow=None):
    """
    Computes the least fixpoint of the function F::

    F(g) = lambda v . bool_expr ? (g v) * loop_meta_state : g v
    """
    state_class = state.__class__

    iteration = 0

    # input state
    loop_state = state

    # initial state values
    entry_state = entry_join_state = exit_join_state = state.empty()
    prev_entry_state = prev_entry_join_state = state.empty()
    prev_loop_state = state.empty()

    while True:
        iteration += 1
        logger.persistent('Iteration', iteration)

        # split state by the conditional of the while loop
        entry_state, exit_state = bool_eval(bool_expr, loop_state)

        # join all exit states together, this is the possible output
        exit_join_state |= exit_state

        # test if fixpoint reached
        entry_join_state = entry_state | prev_entry_join_state
        if _is_fixpoint(
                entry_state, prev_entry_state,
                entry_join_state, prev_entry_join_state,
                iteration):
            break

        # update previous values, which will be used for fixpoint testing in
        # the next iteration
        prev_entry_state = entry_state
        prev_entry_join_state = entry_join_state
        prev_loop_state = loop_state

        # perform loop, what to do depends on if you have a Flow object or a
        # MetaState object
        if loop_flow:
            loop_state = entry_state.transition(loop_flow)
        elif loop_meta_state:
            diff_state = arith_eval_meta_state(loop_meta_state, entry_state)
            # arith_eval_meta_state only computes value changes with
            # loop_meta_state, need to use changes to update existing state
            loop_state = dict(entry_state)
            loop_state.update(diff_state)
            loop_state = state_class(loop_state)
        else:
            raise ValueError(
                'loop_flow and loop_meta_state are both unspecified.')

        # widening
        loop_state = _widen(loop_state, prev_loop_state, iteration)

    logger.unpersistent('Iteration')
    logger.info()

    return {
        'entry': entry_join_state,
        'exit': exit_join_state,
        'last_entry': entry_state,
        'last_exit': loop_state,
    }
