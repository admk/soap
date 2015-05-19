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
        self.iter_var
        self.iter_slice

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

    @property
    def is_pipelined(self):
        return not self.has_inner_loops

    @cached_property
    def iter_var(self):
        bool_expr = self.fix_expr.bool_expr
        iter_var, stop = bool_expr.args
        if not is_variable(iter_var):
            raise ForLoopExtractionFailureException(
                'Cannot extract iteration variable.')
        if iter_var.dtype != int_type:
            raise ForLoopExtractionFailureException(
                'Iteration variable is not an integer.')
        return iter_var

    @cached_property
    def iter_slice(self):
        start = self.start
        if isinstance(start, IntegerInterval):
            start = int(start.to_constant())
        else:
            start = -inf
        stop = self.stop
        if isinstance(stop, IntegerInterval):
            stop = int(stop.to_constant())
        else:
            stop = inf
        step = int(self.step.to_constant())
        return slice(start, stop, step)

    @cached_property
    def start(self):
        return self.fix_expr.init_state[self.iter_var]

    @cached_property
    def stop(self):
        bool_expr = self.fix_expr.bool_expr
        op = bool_expr.op
        _, stop = bool_expr.args
        if stop != expand_expr(stop, self.fix_expr.loop_state):
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

    @cached_property
    def step(self):
        iter_var = self.iter_var
        step = self.fix_expr.loop_state[iter_var]
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
        self.iter_vars = []
        self.iter_slices = []
        self._extract_for_loop_nest(fix_expr)

    @property
    def kernel(self):
        return self._kernel

    def _extract_for_loop_nest(self, fix_expr):
        extractor = ForLoopExtractor(fix_expr)
        loop_var = fix_expr.loop_var
        iter_var = extractor.iter_var
        self.iter_vars.append(iter_var)
        self.iter_slices.append(extractor.iter_slice)

        has_inner_loop = False
        for var, expr in fix_expr.loop_state.items():
            if var == iter_var:
                continue
            if var == loop_var and isinstance(expr, FixExpr):
                self._extract_for_loop_nest(expr)
                has_inner_loop = True
                break

        if not has_inner_loop:
            self._kernel = fix_expr.loop_state
            return

        # if has inner loop, then check the loop is simple
        for var, expr in fix_expr.loop_state.items():
            if var == iter_var or var == loop_var:
                continue
            if var != expr:
                raise ForLoopNestExtractionFailureException(
                    'Loop has logic sandwich.')
