from soap.expression import operators, is_variable, is_expression
from soap.semantics.latency.common import stitch_expr, stitch_env
from soap.semantics.functions import arith_eval, expand_expr


class ForLoopExtractionFailureException(Exception):
    """Failed to extract for loop.  """


class ForLoopExtractor(object):

    def __init__(self, fix_expr, invariant):
        super().__init__()
        bool_expr, loop_state, self.loop_var, _ = fix_expr.args
        bool_label, bool_env = bool_expr
        self.bool_expr = stitch_expr(bool_label, bool_env)
        self.invariant = invariant
        self.label_kernel = loop_state
        self.is_for_loop = True
        try:
            self._init_iter_var()
            self._init_iter_slice()
        except ForLoopExtractionFailureException:
            self.is_for_loop = False

    @property
    def has_inner_loops(self):
        for var, expr in self.label_kernel.items():
            if not is_expression(expr):
                continue
            if expr.op == operators.FIXPOINT_OP:
                return True
        return False

    @property
    def kernel(self):
        try:
            return self._kernel
        except AttributeError:
            pass
        self._kernel = stitch_env(self.label_kernel)
        return self._kernel

    def _init_iter_var(self):
        iter_var, stop_expr = self.bool_expr.args

        if not is_variable(iter_var):
            raise ForLoopExtractionFailureException

        compare_ops = [operators.LESS_OP, operators.LESS_EQUAL_OP]
        if self.bool_expr.op not in compare_ops:
            raise ForLoopExtractionFailureException

        # make sure stop_expr value is not changed throughout loop iterations
        if stop_expr != expand_expr(stop_expr, self.kernel):
            raise ForLoopExtractionFailureException

        self.iter_var = iter_var

    def _init_iter_slice(self):
        iter_var = self.iter_var
        invariant = self.invariant

        step_expr = self.kernel[iter_var]
        if step_expr.op != operators.ADD_OP:
            raise ForLoopExtractionFailureException
        arg_1, arg_2 = step_expr.args
        if arg_1 == iter_var:
            step = arg_2
        elif arg_2 == iter_var:
            step = arg_1
        else:
            raise ForLoopExtractionFailureException
        step = arith_eval(step, invariant)
        if step.min != step.max:
            raise ForLoopExtractionFailureException

        start = invariant[iter_var].min
        stop = invariant[iter_var].max
        step = step.min

        self.iter_slice = slice(start, stop, step)


def extract_loop_nest(fix_expr, invariant):
    loop = ForLoopExtractor(fix_expr, invariant)
    loop_info = {
        'iter_vars': [loop.iter_var],
        'iter_slices': [loop.iter_slice],
        'loop_var': loop.loop_var,
        'invariant': loop.invariant,
        'kernel': loop.kernel,
    }
    return loop_info
