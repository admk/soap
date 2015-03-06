from soap.expression import (
    expression_factory, is_expression, is_variable
)
from soap.semantics.common import is_numeral
from soap.semantics.functions.arithmetic import arith_eval


def expand_expr(expr, meta_state):
    if is_expression(expr):
        args = [expand_expr(a, meta_state) for a in expr.args]
        return expression_factory(expr.op, *args)
    if is_variable(expr):
        try:
            new_expr = meta_state[expr]
        except KeyError:
            raise KeyError(
                'Cannot expand the expression {expr}, missing variable in '
                '{state}'.format(expr=expr, state=meta_state))
        return new_expr
    if is_numeral(expr):
        return expr
    raise TypeError(
        'Do not know how to expand the expression {expr} with expression '
        'state {state}.'.format(expr=expr, state=meta_state))


def _eval_meta_state_with_func(eval_func, meta_state, state):
    mapping = {k: eval_func(v, state) for k, v in meta_state.items()}
    return state.__class__(mapping)


def expand_meta_state(meta_state, state):
    """Expand meta_state with state."""
    return _eval_meta_state_with_func(expand_expr, meta_state, state)


def arith_eval_meta_state(meta_state, state):
    """Perform arithmetic evaluation on meta_state with state."""
    return _eval_meta_state_with_func(arith_eval, meta_state, state)
