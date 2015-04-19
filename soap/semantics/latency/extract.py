from soap.expression import operators, is_variable
from soap.semantics.latency.common import stitch_expr, stitch_env
from soap.semantics.functions import arith_eval, expand_expr


class LoopNestExtractionFailureException(Exception):
    """Failed to extract loop nest.  """


class ForLoopExtractionFailureException(Exception):
    """Failed to extract for loop.  """


def extract_for_loop(fix_expr, invariant):
    bool_expr, loop_state, loop_var, init_state = fix_expr.args

    bool_label, bool_env = bool_expr
    bool_expr = stitch_expr(bool_label, bool_env)

    loop_state = stitch_env(loop_state)

    iter_var, stop = bool_expr.args
    if not is_variable(iter_var):
        raise ForLoopExtractionFailureException

    if bool_expr.op not in [operators.LESS_OP, operators.LESS_EQUAL_OP]:
        raise ForLoopExtractionFailureException

    # make sure stop_expr value is not changed throughout loop iterations
    if stop != expand_expr(stop, loop_state):
        raise ForLoopExtractionFailureException

    step_expr = loop_state[iter_var]
    if step_expr.op != operators.ADD_OP:
        raise ForLoopExtractionFailureException
    arg_1, arg_2 = step_expr.args
    if arg_1 == iter_var:
        step = arg_2
    elif arg_2 == iter_var:
        step = arg_1
    else:
        raise ForLoopExtractionFailureException

    start = invariant[iter_var].min
    stop = invariant[iter_var].max
    step = arith_eval(step, invariant)
    if step.min != step.max:
        raise ForLoopExtractionFailureException
    step = step.min

    loop_info = {
        'iter_var': iter_var,
        'iter_slice': slice(start, stop, step),
        'loop_var': loop_var,
        'invariant': invariant,
    }
    return loop_info


def extract_loop_nest(fix_expr, invariant):
    loop = extract_for_loop(fix_expr, invariant)
    loop_info = {
        'iter_vars': [loop['iter_var']],
        'iter_slices': [loop['iter_slice']],
        'loop_var': loop['loop_var'],
        'invariant': loop['invariant'],
    }
    return loop_info
