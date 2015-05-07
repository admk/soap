from soap.common.formatting import underline

from soap.datatype import int_type
from soap.expression.operators import (
    FIXPOINT_OP, UNROLL_OP, FOR_OP, LESS_OP, ADD_OP
)
from soap.expression.arithmetic import (
    ArithExpr, TernaryArithExpr, QuaternaryArithExpr, BinaryArithExpr,
)
from soap.expression.boolean import BinaryBoolExpr
from soap.semantics.error import IntegerInterval


class FixExprIsNotForLoopException(Exception):
    """FixExpr object is not a for loop.  """


class FixExpr(QuaternaryArithExpr):
    """Fixpoint expression."""

    def __init__(self, a1, a2, a3, a4):
        super().__init__(FIXPOINT_OP, a1, a2, a3, a4)

    @property
    def bool_expr(self):
        return self.a1

    @property
    def loop_state(self):
        return self.a2

    @property
    def loop_var(self):
        return self.a3

    @property
    def init_state(self):
        return self.a4

    def format(self):
        fixpoint_var = underline('e')
        s = ('{op}(λ{fvar}.({bool_expr} ? {fvar} % {loop_state} : {var}))'
             ' % {init_state}')
        return s.format(
            fvar=fixpoint_var, op=self.op, bool_expr=self.bool_expr,
            loop_state=self.loop_state.format(), var=self.loop_var,
            init_state=self.init_state.format())


class UnrollExpr(TernaryArithExpr):
    def __init__(self, a1, a2, a3):
        super().__init__(UNROLL_OP, a1, a2, a3)

    @property
    def fix_expr(self):
        return self.a1

    @property
    def outer(self):
        return self.a2

    @property
    def depth(self):
        return self.a3

    def format(self):
        fix_expr, outer, depth = self._args_to_str()
        return '{} @ {}'.format(fix_expr, depth)


class ForExpr(ArithExpr):
    def __init__(self, iter_var, start_expr, stop_expr, step_expr,
                 loop_state, loop_var, init_state):
        if iter_var not in loop_state:
            loop_state = loop_state.immu_update(iter_var, iter_var)
        super().__init__(
            FOR_OP, iter_var, start_expr, stop_expr, step_expr,
            loop_state, loop_var, init_state)

    @property
    def iter_var(self):
        return self.args[0]

    @property
    def start_expr(self):
        return self.args[1]

    @property
    def stop_expr(self):
        return self.args[2]

    @property
    def step_expr(self):
        return self.args[3]

    @property
    def loop_state(self):
        return self.args[4]

    @property
    def loop_var(self):
        return self.args[5]

    @property
    def init_state(self):
        return self.args[6]

    def to_fix_expr(self):
        from soap.semantics.functions.meta import expand_expr

        start_expr = expand_expr(self.start_expr, self.init_state)
        init_state = self.init_state.immu_update(self.iter_var, start_expr)
        bool_expr = BinaryBoolExpr(LESS_OP, self.iter_var, self.stop_expr)
        incr_expr = BinaryArithExpr(ADD_OP, self.iter_var, self.step_expr)
        incr_expr = expand_expr(incr_expr, self.loop_state)
        loop_state = self.loop_state.immu_update(self.iter_var, incr_expr)

        return FixExpr(bool_expr, loop_state, self.loop_var, init_state)

    @property
    def has_fixed_iter_pattern(self):
        from soap.semantics.functions.meta import expand_expr

        if self.iter_var.dtype != int_type:
            return False
        step = self.step_expr
        if not (isinstance(step, IntegerInterval) and step.min == step.max):
            return False
        stop = self.stop_expr
        if stop != expand_expr(stop, self.loop_state):
            return False
        return True

    @property
    def has_inner_loops(self):
        from soap.semantics.functions.label import _label
        from soap.semantics.state.box import BoxState
        from soap.expression.common import is_expression

        _, label_loop_state = _label(
            self.loop_state, BoxState(bottom=True), None)
        for var, expr in label_loop_state.items():
            if not is_expression(expr):
                continue
            if expr.op == FIXPOINT_OP:
                return True
        return False

    @property
    def is_pipelineable(self):
        return self.has_fixed_iter_pattern and not self.has_inner_loops

    def format(self):
        s = ('{op}({iter_var} = {start}, {stop}, {step}; {loop_state}; '
             '{loop_var}) % {init_state}')
        return s.format(
            op=self.op, iter_var=self.iter_var, start=self.start_expr,
            stop=self.stop_expr, step=self.step_expr,
            loop_state=self.loop_state.format(), loop_var=self.loop_var,
            init_state=self.init_state.format())
