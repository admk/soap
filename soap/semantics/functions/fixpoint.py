from soap import logger
from soap.context import context
from soap.common.cache import cached
from soap.expression import FixExpr, SelectExpr
from soap.semantics.functions.boolean import bool_eval
from soap.semantics.functions.meta import arith_eval_meta_state, expand_expr


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
        if iteration % context.widen_factor == 0:
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

    return {
        'entry': entry_join_state,
        'exit': exit_join_state,
        'last_entry': entry_state,
        'last_exit': loop_state,
    }


def fix_expr_eval(expr, state):
    state = arith_eval_meta_state(expr.init_state, state)
    fixpoint = fixpoint_eval(
        state, expr.bool_expr, loop_meta_state=expr.loop_state)
    fixpoint['last_entry']._warn_non_termination(expr)
    return fixpoint['exit'][expr.loop_var]


def _equivalent_loop_meta_state(expr, outer_state, depth):
    from soap.semantics.state.meta import MetaState

    unroll_state = expr.loop_state
    expanded_bool_expr = expand_expr(expr.bool_expr, outer_state)

    for _ in range(depth):
        new_unroll_state = {}
        for var, expr in unroll_state.items():
            true_expr = expand_expr(expr, outer_state)
            false_expr = outer_state[var]
            if true_expr == false_expr:
                new_unroll_state[var] = true_expr
            else:
                expr = SelectExpr(
                    expanded_bool_expr, true_expr, false_expr)
                new_unroll_state[var] = expr
        unroll_state = new_unroll_state

    return MetaState(unroll_state)


def equivalent_loop_meta_states(expr, depth):
    for d in range(depth + 1):
        yield _equivalent_loop_meta_state(expr, expr.loop_state, d)


def unroll_eval(expr, outer, state, depth):
    bool_expr = expr.bool_expr
    loop_meta_state = _equivalent_loop_meta_state(expr, outer, depth)
    unrolled_expr = FixExpr(
        bool_expr, loop_meta_state, expr.loop_var, expr.init_state)
    return fix_expr_eval(unrolled_expr, state)
