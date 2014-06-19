from soap.expression import (
    expression_factory, is_expression, is_variable
)
from soap.semantics.common import is_numeral
from soap.semantics.functions.arithmetic import arith_eval


def to_meta_state(flow):
    from soap.semantics.state.meta import MetaState
    id_state = MetaState({v: v for v in flow.vars(output=False)})
    return id_state.transition(flow)


def expand_expr(expr, meta_state):
    if is_expression(expr):
        args = [expand_expr(a, meta_state) for a in expr.args]
        return expression_factory(expr.op, *args)
    if is_variable(expr):
        return meta_state[expr]
    if is_numeral(expr):
        return expr
    raise TypeError(
        'Do not know how to expand the expression {expr} with expression '
        'state {state}.'.format(expr=expr, state=meta_state))


def _eval_meta_state_with_func(eval_func, state, meta_state):
    mapping = {k: eval_func(v, state) for k, v in meta_state.items()}
    return state.__class__(mapping)


def expand_meta_state(meta_state, state):
    """Expand meta_state with state."""
    return _eval_meta_state_with_func(expand_expr, meta_state, state)


def arith_eval_meta_state(state, meta_state):
    """Perform arithmetic evaluation on meta_state with state."""
    return _eval_meta_state_with_func(arith_eval, state, meta_state)
