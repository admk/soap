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


def bool_eval(state, expr):
    """
    Supports only simple boolean expressions::
        <variable> <operator> <arithmetic expression>
    For example::
        x <= 3 * y.

    Returns:
        Two states, respectively satisfying or dissatisfying the conditional.
    """
    for cond in True, False:
        var, cstr = _conditional(state, expr, cond)
        if cstr.is_bottom():
            yield state.empty()
        else:
            yield state[var:cstr]


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
