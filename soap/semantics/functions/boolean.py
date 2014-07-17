from soap.common.cache import cached
from soap.expression import (
    LESS_OP, GREATER_OP, LESS_EQUAL_OP, GREATER_EQUAL_OP,
    EQUAL_OP, NOT_EQUAL_OP, is_variable
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


def _constraint(op, cond, bound):
    from soap.semantics.state.constraint import constraint_negate_dict
    op = constraint_negate_dict[op] if not cond else op
    if bound.is_bottom():
        return bound
    bound_min, bound_max = _contract(op, bound)
    if op == EQUAL_OP:
        return bound
    if op == NOT_EQUAL_OP:
        return bound.__class__([-inf, inf])
    if op in [LESS_OP, LESS_EQUAL_OP]:
        return bound.__class__([-inf, bound_max])
    if op in [GREATER_OP, GREATER_EQUAL_OP]:
        return bound.__class__([bound_min, inf])
    raise ValueError('Unknown boolean operator %s' % op)


def _conditional(op, var, expr, state, cond):
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


_mirror_dict = {
    LESS_OP: GREATER_OP,
    LESS_EQUAL_OP: GREATER_EQUAL_OP,
    GREATER_OP: LESS_OP,
    GREATER_EQUAL_OP: LESS_EQUAL_OP,
    EQUAL_OP: EQUAL_OP,
    NOT_EQUAL_OP: NOT_EQUAL_OP,
}


@cached
def bool_eval(expr, state):
    """
    Supports only simple boolean expressions::
        <variable> <operator> <arithmetic expression>
    Or::
        <arithmetic expression> <operator> <variable>

    For example::
        x <= 3 * y.

    Returns:
        Two states, respectively satisfying or dissatisfying the conditional.
    """
    op = expr.op
    a1, a2 = expr.args
    args_swap_list = [(op, a1, a2), (_mirror_dict[op], a2, a1)]
    split_list = []
    for cond in True, False:
        cstr_list = []
        for cond_op, cond_var, cond_expr in args_swap_list:
            if not is_variable(cond_var):
                continue
            cstr = _conditional(cond_op, cond_var, cond_expr, state, cond)
            cstr_list.append(cstr)
        if any(cstr.is_bottom() for _, cstr in cstr_list):
            split = state.empty()
        else:
            split = state
            for var, cstr in cstr_list:
                split = split[var:cstr]
        split_list.append(split)
    return tuple(split_list)
