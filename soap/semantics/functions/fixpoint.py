import math

from soap import logger
from soap.context import context
from soap.common.cache import cached
from soap.expression import (
    operators, BinaryArithExpr, BinaryBoolExpr, FixExpr, SelectExpr
)
from soap.semantics.error import IntegerInterval
from soap.semantics.functions.boolean import bool_eval
from soap.semantics.functions.label import label
from soap.semantics.functions.meta import (
    arith_eval_meta_state, expand_expr, expand_meta_state
)


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
        logger.persistent('Iteration', iteration, l=logger.levels.debug)

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


def _unroll_fix_expr(fix_expr, outer_state, depth):
    from soap.semantics.state.meta import MetaState

    unroll_state = fix_expr.loop_state
    expanded_bool_expr = expand_expr(fix_expr.bool_expr, outer_state)

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

    loop_state = MetaState(unroll_state)
    fix_expr = FixExpr(
        fix_expr.bool_expr, loop_state, fix_expr.loop_var, fix_expr.init_state)
    return fix_expr


def _unroll_for_loop(expr, extractor, depth):
    from soap.semantics.state.meta import MetaState

    yield expr
    loop_state = expr.loop_state
    init_state = expr.init_state
    loop_var = expr.loop_var
    iter_var = extractor.iter_var
    iter_slice = extractor.iter_slice
    start, stop, step = iter_slice.start, iter_slice.stop, iter_slice.step

    for d in range(2, depth + 1):
        # FIXME non-constant bounds
        count = int(math.floor((stop - start) / step))
        new_step = step * d
        new_count = int(math.floor(count / d))
        new_stop = start + (new_count * d - 1) * step
        prologue_start = new_stop + step

        new_loop_state = loop_state
        for _ in range(d - 1):
            new_loop_state = expand_meta_state(new_loop_state, loop_state)

        step_expr = BinaryArithExpr(
            operators.ADD_OP, iter_var, IntegerInterval(new_step))
        new_loop_state = new_loop_state.immu_update(iter_var, step_expr)

        bool_expr = BinaryBoolExpr(
            operators.LESS_EQUAL_OP, iter_var, IntegerInterval(new_stop))

        fix_expr = FixExpr(bool_expr, new_loop_state, loop_var, init_state)

        loop_expr = loop_state[loop_var]
        id_state = MetaState({var: var for var in loop_expr.vars()})
        epilogue = []
        for i in range(prologue_start, stop + 1, step):
            state = id_state.immu_update(iter_var, IntegerInterval(i))
            epilogue.append(expand_expr(loop_expr, state))

        state = MetaState({loop_var: fix_expr})
        for expr in epilogue:
            expr_state = MetaState({loop_var: expr})
            state = expand_meta_state(expr_state, state)

        yield state[loop_var]


def unroll_fix_expr(expr, state, depth):
    from soap.semantics.latency.extract import ForLoopExtractor
    expr_label, env = label(expr, state, None)
    extractor = ForLoopExtractor(env[expr_label], expr_label.invariant)
    if extractor.is_for_loop:
        if extractor.has_inner_loops:
            yield expr
        else:
            yield from _unroll_for_loop(expr, extractor, depth)
    else:
        for d in range(depth + 1):
            yield _unroll_fix_expr(expr, expr.loop_state, d)


def unroll_eval(expr, outer, state, depth):
    unrolled_expr = _unroll_fix_expr(expr, outer, depth)
    return fix_expr_eval(unrolled_expr, state)
