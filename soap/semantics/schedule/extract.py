from soap.common.cache import cached_property
from soap.datatype import int_type
from soap.expression import (
    operators, is_variable, is_expression, BinaryArithExpr, FixExpr
)
from soap.semantics.error import IntegerInterval, inf
from soap.semantics.functions import expand_expr, label


class ForLoopExtractionFailureException(Exception):
    """Failed to extract for loop.  """


class ForLoopExtractor(object):
    def __init__(self, fix_expr):
        super().__init__()
        self.fix_expr = fix_expr
        self.is_for_loop = True
        try:
            self.iter_var = self._extract_iter_var(fix_expr)
            self.iter_slice = self._extract_iter_slice(fix_expr, self.iter_var)
        except ForLoopExtractionFailureException:
            self.is_for_loop = False

    @property
    def kernel(self):
        return self.fix_expr.loop_state

    @cached_property
    def label_kernel(self):
        _, kernel = label(self.kernel, None, None, fusion=False)
        return kernel

    @cached_property
    def has_inner_loops(self):
        for var, expr in self.label_kernel.items():
            if not is_expression(expr):
                continue
            if expr.op == operators.FIXPOINT_OP:
                return True
        return False

    def _extract_iter_var(self, fix_expr):
        bool_expr = fix_expr.bool_expr
        iter_var, stop = bool_expr.args
        if not is_variable(iter_var):
            raise ForLoopExtractionFailureException(
                'Cannot extract iteration variable.')
        if iter_var.dtype != int_type:
            raise ForLoopExtractionFailureException(
                'Iteration variable is not an integer.')
        return iter_var

    def _extract_iter_slice(self, fix_expr, iter_var):
        start = self._extract_start(fix_expr, iter_var)
        if isinstance(start, IntegerInterval):
            start = int(start.to_constant())
        else:
            start = -inf
        stop = self._extract_stop(fix_expr)
        if isinstance(stop, IntegerInterval):
            stop = int(stop.to_constant())
        else:
            stop = inf
        step = int(self._extract_step(fix_expr, iter_var).to_constant())
        return slice(start, stop, step)

    def _extract_start(self, fix_expr, iter_var):
        return fix_expr.init_state[self.iter_var]

    def _extract_stop(self, fix_expr):
        bool_expr = fix_expr.bool_expr
        op = bool_expr.op
        _, stop = bool_expr.args
        if stop != expand_expr(stop, fix_expr.loop_state):
            raise ForLoopExtractionFailureException(
                'Stop value changes in loop.')
        if op == operators.LESS_EQUAL_OP:
            if isinstance(stop, IntegerInterval):
                stop += IntegerInterval(1)
            else:
                stop = BinaryArithExpr(operators.ADD_OP, stop, 1)
        elif op not in [operators.LESS_OP, operators.NOT_EQUAL_OP]:
            raise ForLoopExtractionFailureException(
                'Unrecognized compare operator.')
        return stop

    def _extract_step(self, fix_expr, iter_var):
        step = fix_expr.loop_state[iter_var]
        if step.op != operators.ADD_OP:
            raise ForLoopExtractionFailureException(
                'Step expression must increment.')
        arg_1, arg_2 = step.args
        if arg_1 == iter_var:
            step = arg_2
        elif arg_2 == iter_var:
            step = arg_1
        else:
            raise ForLoopExtractionFailureException(
                'Step expression must contain iteration variable.')
        if not (isinstance(step, IntegerInterval) and step.min == step.max):
            raise ForLoopExtractionFailureException(
                'Step must be constant in a for loop.')
        if step.min <= 0:
            raise ForLoopExtractionFailureException(
                'Step value must be positive.')
        return step


class ForLoopNestExtractionFailureException(Exception):
    """Failed to extract for loop nest.  """


class ForLoopNestExtractor(ForLoopExtractor):
    def __init__(self, fix_expr):
        super().__init__(fix_expr)
        try:
            self.iter_vars, self.iter_slices, self._kernel = \
                self._extract_for_loop_nest(fix_expr)
            self.is_for_loop_nest = True
        except ForLoopNestExtractionFailureException:
            self.iter_vars = self.iter_slices = None
            self._kernel = fix_expr.loop_state
            self.is_for_loop_nest = False

    @property
    def kernel(self):
        return self._kernel

    def _extract_for_loop_nest(self, fix_expr):
        extractor = ForLoopExtractor(fix_expr)
        if not extractor.is_for_loop:
            raise ForLoopNestExtractionFailureException(
                'Loop is not for loop.')
        loop_var = fix_expr.loop_var
        iter_var = extractor.iter_var
        iter_vars = [iter_var]
        iter_slices = [extractor.iter_slice]

        for var, expr in fix_expr.loop_state.items():
            if var == iter_var:
                continue
            if var == loop_var:
                if isinstance(expr, FixExpr):
                    # has inner loop
                    inner_fix_expr = expr
                    break
                return iter_vars, iter_slices, fix_expr.loop_state
        else:
            raise ForLoopNestExtractionFailureException(
                'Did not find loop_var in loop.')

        # if has inner loop, then check the outer loop is simple
        for var, expr in fix_expr.loop_state.items():
            if var == iter_var or var == loop_var:
                continue
            if var != expr:
                raise ForLoopNestExtractionFailureException(
                    'Loop has logic sandwich.')

        inner_iter_vars, inner_iter_slices, inner_kernel = \
            self._extract_for_loop_nest(inner_fix_expr)
        iter_vars += inner_iter_vars
        iter_slices += inner_iter_slices
        return iter_vars, iter_slices, inner_kernel
