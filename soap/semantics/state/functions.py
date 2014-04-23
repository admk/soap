from soap import logger
from soap.context import context
from soap.common.cache import cached
from soap.expression import (
    LESS_OP, GREATER_OP, LESS_EQUAL_OP, GREATER_EQUAL_OP,
    EQUAL_OP, NOT_EQUAL_OP, Expression, Variable,
    expression_factory, is_expression, is_variable
)
from soap.semantics.common import is_numeral
from soap.semantics.error import (
    inf, ulp, mpz_type, mpfr_type,
    IntegerInterval, FloatInterval, ErrorSemantics
)


@cached
def arith_eval(state, expr):
    """Evaluates an expression with state's mapping."""
    if isinstance(expr, Variable):
        return state[expr]
    if isinstance(expr, Expression):
        return expr.eval(state)
    if isinstance(expr, (IntegerInterval, FloatInterval, ErrorSemantics)):
        return expr
    if isinstance(expr, (mpz_type, mpfr_type)):
        return expr
    raise TypeError('Do not know how to evaluate {!r}'.format(expr))


def _rhs_eval(state, expr):
    bound = arith_eval(state, expr)
    if isinstance(bound, (int, mpz_type)):
        return IntegerInterval(bound)
    if isinstance(bound, (float, mpfr_type)):
        return FloatInterval(bound)
    if isinstance(bound, IntegerInterval):
        return bound
    if isinstance(bound, ErrorSemantics):
        # It cannot handle incorrect branching due to error in
        # evaluation of the expression.
        return bound.v
    raise TypeError(
        'Evaluation returns an unrecognized object: %r' % bound)


def _contract(op, bound):
    if op not in [LESS_OP, GREATER_OP]:
        return bound.min, bound.max
    if isinstance(bound, IntegerInterval):
        bmin = bound.min + 1
        bmax = bound.max - 1
    elif isinstance(bound, FloatInterval):
        bmin = bound.min + ulp(bound.min)
        bmax = bound.max - ulp(bound.max)
    else:
        raise TypeError
    return bmin, bmax


_negate_dict = {
    LESS_OP: GREATER_EQUAL_OP,
    LESS_EQUAL_OP: GREATER_OP,
    GREATER_OP: LESS_EQUAL_OP,
    GREATER_EQUAL_OP: LESS_OP,
    EQUAL_OP: NOT_EQUAL_OP,
    NOT_EQUAL_OP: EQUAL_OP,
}


def _constraint(op, cond, bound):
    op = _negate_dict[op] if not cond else op
    if bound.is_bottom():
        return bound
    bound_min, bound_max = _contract(op, bound)
    if op == EQUAL_OP:
        return bound
    if op == NOT_EQUAL_OP:
        raise NotImplementedError
    if op in [LESS_OP, LESS_EQUAL_OP]:
        return bound.__class__([-inf, bound_max])
    if op in [GREATER_OP, GREATER_EQUAL_OP]:
        return bound.__class__([bound_min, inf])
    raise ValueError('Unknown boolean operator %s' % op)


def _conditional(state, expr, cond):
    bound = _rhs_eval(state, expr.a2)
    if isinstance(state[expr.a1], (FloatInterval, ErrorSemantics)):
        # Comparing floats
        bound = FloatInterval(bound)
    cstr = _constraint(expr.op, cond, bound)
    if isinstance(cstr, FloatInterval):
        cstr = ErrorSemantics(cstr, FloatInterval(top=True))
    cstr &= state[expr.a1]
    bot = isinstance(cstr, ErrorSemantics) and cstr.v.is_bottom()
    bot = bot or cstr.is_bottom()
    if bot:
        return expr.a1, cstr.__class__(bottom=True)
    return expr.a1, cstr


@cached
def bool_eval(state, expr):
    """
    Supports only simple boolean expressions::
        <variable> <operator> <arithmetic expression>
    For example::
        x <= 3 * y.

    Returns:
        Two states, respectively satisfying or dissatisfying the conditional.
    """
    splits = []
    for cond in True, False:
        var, cstr = _conditional(state, expr, cond)
        if cstr.is_bottom():
            split = state.empty()
        else:
            split = state[var:cstr]
        splits.append(split)
    return splits


def to_meta_state(flow):
    from soap.semantics.state.meta import MetaState
    id_state = MetaState({v: v for v in flow.vars()})
    return id_state.transition(flow)


def expand_expr(meta_state, expr):
    if is_expression(expr):
        args = [expand_expr(meta_state, a) for a in expr.args]
        return expression_factory(expr.op, *args)
    if is_variable(expr):
        return meta_state[expr]
    if is_numeral(expr):
        return expr
    raise TypeError(
        'Do not know how to expand the expression {expr} with expression '
        'state {state}.'.format(expr=expr, state=meta_state))


def _eval_meta_state_with_func(eval_func, state, meta_state):
    mapping = {k: eval_func(state, v) for k, v in meta_state.items()}
    return state.__class__(mapping)


def expand_meta_state(state, meta_state):
    """Expand meta_state with state."""
    return _eval_meta_state_with_func(expand_expr, state, meta_state)


def arith_eval_meta_state(state, meta_state):
    """Perform arithmetic evaluation on meta_state with state."""
    return _eval_meta_state_with_func(arith_eval, state, meta_state)


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
        entry_state, exit_state = bool_eval(loop_state, bool_expr)

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
            diff_state = arith_eval_meta_state(entry_state, loop_meta_state)
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
