from soap.common.cache import cached
from soap.expression import (
    LESS_OP, GREATER_OP, LESS_EQUAL_OP, GREATER_EQUAL_OP,
    EQUAL_OP, NOT_EQUAL_OP
)
from soap.semantics.error import (
    inf, ulp, mpz_type, mpfr_type,
    IntegerInterval, FloatInterval, ErrorSemantics
)


def _rhs_eval(expr, state):
    from soap.semantics.functions.arithmetic import arith_eval
    bound = arith_eval(expr, state)
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


def _conditional(var, op, expr, state, cond):
    bound = _rhs_eval(expr, state)
    if isinstance(state[var], (FloatInterval, ErrorSemantics)):
        # Comparing floats
        bound = FloatInterval(bound)
    cstr = _constraint(op, cond, bound)
    if isinstance(cstr, FloatInterval):
        cstr = ErrorSemantics(cstr, FloatInterval(top=True))
    cstr &= state[var]
    bot = isinstance(cstr, ErrorSemantics) and cstr.v.is_bottom()
    bot = bot or cstr.is_bottom()
    if bot:
        return var, cstr.__class__(bottom=True)
    return var, cstr


@cached
def bool_eval(expr, state):
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
        var, cstr = _conditional(expr.a1, expr.op, expr.a2, state, cond)
        if cstr.is_bottom():
            split = state.empty()
        else:
            split = state[var:cstr]
        splits.append(split)
    return splits
