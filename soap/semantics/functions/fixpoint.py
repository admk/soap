from soap import logger
from soap.context import context
from soap.common.cache import cached
from soap.expression import (
    operators, BinaryArithExpr, BinaryBoolExpr, FixExpr, SelectExpr,
    fix_expr_has_inner_loop
)
from soap.semantics.error import IntegerInterval, ErrorSemantics
from soap.semantics.functions.arithmetic import arith_eval
from soap.semantics.functions.boolean import bool_eval
from soap.semantics.functions.meta import (
    expand_expr, expand_meta_state
)
from soap.semantics.linalg import MultiDimensionalArray


def _is_fixpoint(state, prev_state, curr_join_state, prev_join_state,
                 iteration):
    if context.unroll_factor > 0 and iteration % context.unroll_factor == 0:
        # join all states in previous iterations
        logger.info('No unroll', iteration)
        return curr_join_state.is_fixpoint(prev_join_state)
    return state.is_fixpoint(prev_state)


def _widen(obj, prev_obj, iteration):
    if context.widen_factor > 0 and iteration % context.widen_factor == 0:
        logger.info('Widening', iteration)
        obj = prev_obj.widen(obj)
    return obj


def _extrapolate(value, factor):
    from soap.semantics.state import BoxState
    if isinstance(value, int):
        return value
    if isinstance(value, ErrorSemantics):
        e, v = value
        return ErrorSemantics(e * factor, v * factor)
    if isinstance(value, IntegerInterval):
        return value
    if isinstance(value, MultiDimensionalArray):
        if value.is_scalar:
            scalar = _extrapolate(value.scalar, factor)
            return value.__class__(scalar=scalar, _shape=value.shape)
        items = [_extrapolate(val, factor) for val in value._flat_items]
        return value.__class__(_flat_items=items, _shape=value.shape)
    if isinstance(value, BoxState):
        return BoxState({
            key: _extrapolate(key_value, factor)
            for key, key_value in value.items()})
    raise TypeError('Do not know how to extrapolate {}'.format(value))


class TripCount(object):
    def __init__(self, fix_expr):
        super().__init__()
        self.fix_expr = fix_expr
        self._trip_count = None

    def get(self):
        trip_count = self._trip_count
        if trip_count is not None:
            return trip_count
        from soap.semantics.schedule.extract import ForLoopNestExtractor
        extractor = ForLoopNestExtractor(self.fix_expr)
        try:
            trip_count = extractor.trip_count
        except AttributeError:
            logger.warning(
                'Failed to find trip count for loop {}, reason: {}'
                .format(self.fix_expr, extractor.exception))
            trip_count = None
        self._trip_count = trip_count
        return trip_count


def _is_fast_finish(
        iteration, entry_state, entry_join_state, exit_join_state, loop_state,
        loop_end_join_state, trip_count):

    fast_factor = context.fast_factor
    if fast_factor >= 1:
        return

    curr_factor = iteration / trip_count
    if curr_factor < fast_factor:
        return

    info = {
        'entry': entry_join_state,
        'exit': exit_join_state | loop_state,
        'last_entry': entry_state,
        'last_exit': loop_state,
        'end': loop_end_join_state,
    }
    factor = curr_factor / fast_factor
    info = {
        key: value if value.is_bottom() else
        _extrapolate(value, factor) for key, value in info.items()}
    info.update(trip_count=trip_count, path='fast_factor')
    return info


@cached
def fixpoint_eval(fix_expr, state, run_init_state=False):
    """
    Computes the least fixpoint of the function F::

    F(g) = lambda v . {
        (g v) * loop_state   if bool_expr v == true
        g v                  otherwise
    """
    from soap.semantics.state import BoxState

    state = state or BoxState(bottom=True)

    if run_init_state:
        state = arith_eval(fix_expr.init_state, state)

    if state.is_bottom():
        # shortcut for bottom values
        return {
            'entry': state,
            'exit': state,
            'last_entry': state,
            'last_exit': state,
            'end': state,
            'trip_count': 0,
            'path': 'bottom_shortcut',
        }

    loop_meta_state = fix_expr.loop_state
    bool_expr = fix_expr.bool_expr
    trip_count = TripCount(fix_expr)

    if context.fast_outer and fix_expr_has_inner_loop(fix_expr):
        exit_state = arith_eval(loop_meta_state, state)
        return {
            'entry': state,
            'exit': exit_state,
            'last_entry': state,
            'last_exit': exit_state,
            'end': exit_state,
            'trip_count': trip_count.get(),
            'path': 'fast_outer',
        }

    iteration = 0
    state_class = state.__class__

    # input state
    loop_state = state

    # initial state values
    entry_state = entry_join_state = exit_join_state = state.empty()
    prev_entry_state = prev_entry_join_state = state.empty()
    prev_loop_state = loop_end_join_state = state.empty()

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

        # fast iteration
        info = _is_fast_finish(
            iteration, entry_state, entry_join_state, exit_join_state,
            loop_state, loop_end_join_state, trip_count.get())
        if info is not None:
            return info

        # update previous values, which will be used for fixpoint testing in
        # the next iteration
        prev_entry_state = entry_state
        prev_entry_join_state = entry_join_state
        prev_loop_state = loop_state

        # analyze loop body
        diff_state = arith_eval(loop_meta_state, entry_state)
        # arith_eval only computes value changes with loop_meta_state,
        # need to use changes to update existing state
        loop_state = dict(entry_state)
        loop_state.update(diff_state)
        loop_state = state_class(loop_state)

        loop_end_join_state = loop_state | loop_end_join_state

        # widening
        loop_state = _widen(loop_state, prev_loop_state, iteration)

    logger.unpersistent('Iteration')

    return {
        'entry': entry_join_state,
        'exit': exit_join_state,
        'last_entry': entry_state,
        'last_exit': loop_state,
        'end': loop_end_join_state,
        'trip_count': iteration,
        'path': 'normal',
    }


def fix_expr_eval(expr, state):
    fixpoint = fixpoint_eval(expr, state, run_init_state=True)
    last_entry = fixpoint['last_entry']
    if fixpoint['path'] not in ['fast_factor', 'fast_outer']:
        if last_entry is not None and not last_entry.is_bottom():
            logger.warning(
                'Loop/fixpoint computation "{}" may never terminate with state'
                ' {}, and analysis path "{}", assuming it always terminates.'
                .format(expr, state, fixpoint['path']))
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
    fix_expr.unroll_depth = depth
    return fix_expr


def _unroll_for_loop(expr, iter_var, iter_slice, depth):
    from soap.semantics.state.meta import MetaState
    from soap.semantics.schedule.common import iter_point_count
    from soap.transformer.linalg import linear_algebra_simplify

    expr = linear_algebra_simplify(expr)
    expr.unroll_depth = 0
    expr_list = [expr]

    loop_state = expr.loop_state
    init_state = expr.init_state
    loop_var = expr.loop_var
    start, stop, step = iter_slice.start, iter_slice.stop, iter_slice.step
    if any(not isinstance(value, int) for value in (start, stop, step)):
        # TODO support expression bounds (if Xilinx supports this)
        logger.warning('Non-constant bounds not supported in unrolling yet.')
        return expr_list

    for d in range(2, depth + 2):
        new_step = step * d
        new_count = iter_point_count(slice(start, stop, new_step))
        mid = start + new_count * new_step

        new_loop_state = loop_state
        for _ in range(d - 1):
            new_loop_state = expand_meta_state(new_loop_state, loop_state)

        step_expr = BinaryArithExpr(
            operators.ADD_OP, iter_var, IntegerInterval(new_step))
        new_loop_state = new_loop_state.immu_update(iter_var, step_expr)
        new_loop_state = linear_algebra_simplify(new_loop_state)

        bool_expr = BinaryBoolExpr(
            operators.LESS_OP, iter_var, IntegerInterval(mid))

        fix_expr = FixExpr(bool_expr, new_loop_state, loop_var, init_state)
        fix_expr.unroll_depth = d

        loop_expr = loop_state[loop_var]
        id_state = MetaState({var: var for var in loop_expr.vars()})
        epilogue = []
        for i in range(mid, stop, step):
            state = id_state.immu_update(iter_var, IntegerInterval(i))
            epilogue.append(expand_expr(loop_expr, state))

        epilogue_state = id_state.immu_update(loop_var, fix_expr)
        for expr in epilogue:
            expr_state = id_state.immu_update(loop_var, expr)
            epilogue_state = expand_meta_state(expr_state, epilogue_state)

        expr_list.append(epilogue_state[loop_var])

    return expr_list


def unroll_fix_expr(expr, depth):
    from soap.semantics.schedule.extract import ForLoopExtractor

    extractor = ForLoopExtractor(expr)
    if extractor.has_inner_loops:
        expr.unroll_depth = 0
        return [expr]

    if not extractor.is_for_loop:
        return [_unroll_fix_expr(expr, expr.loop_state, d)
                for d in range(depth + 1)]

    iter_var = extractor.iter_var
    iter_slice = extractor.iter_slice
    return _unroll_for_loop(expr, iter_var, iter_slice, depth)
