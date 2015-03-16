from soap.common.formatting import underline

from soap.expression.operators import (
    FIXPOINT_OP, UNROLL_OP, FOR_OP, LESS_EQUAL_OP, ADD_OP
)
from soap.expression.arithmetic import (
    ArithExpr, TernaryArithExpr, QuaternaryArithExpr, BinaryArithExpr,
)
from soap.expression.boolean import BinaryBoolExpr


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

    def __str__(self):
        fixpoint_var = underline('e')
        s = ('{op}(λ{fvar}.({bool_expr} ? {fvar} % {loop_state} : {var}))'
             ' % {init_state}')
        return s.format(
            fvar=fixpoint_var, op=self.op, bool_expr=self.bool_expr,
            loop_state=self.loop_state, var=self.loop_var,
            init_state=self.init_state)


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

    def __str__(self):
        fix_expr, outer, depth = self._args_to_str()
        return '{} @ {}'.format(fix_expr, depth)


class ForExpr(ArithExpr):
    def __init__(self, iter_var, start_expr, stop_expr, step_expr,
                 loop_state, loop_var, init_state):
        super().__init__(
            FOR_OP, iter_var, start_expr, stop_expr, step_expr,
            loop_state, loop_var, init_state)

    @property
    def iter_var(self):
        return self.a1

    @property
    def start_expr(self):
        return self.a2

    @property
    def stop_expr(self):
        return self.a3

    @property
    def step_expr(self):
        return self.a4

    @property
    def loop_state(self):
        return self.a5

    @property
    def loop_var(self):
        return self.a6

    @property
    def init_state(self):
        return self.a7

    def to_fix_expr(self):
        from soap.semantics.functions.meta import expand_expr
        start_expr = expand_expr(self.start_expr, self.init_state)
        init_state = self.init_state.immu_update(self.iter_var, start_expr)
        bool_expr = BinaryBoolExpr(
            LESS_EQUAL_OP, self.iter_var, self.stop_expr)
        incr_expr = BinaryArithExpr(
            ADD_OP, self.iter_var, self.step_expr)
        incr_expr = expand_expr(incr_expr, self.loop_state)
        loop_state = self.loop_state.immu_update(self.iter_var, incr_expr)
        return FixExpr(bool_expr, loop_state, self.loop_var, init_state)

    @property
    def has_fixed_iter_pattern(self):
        from soap.semantics.functions.meta import expand_expr
        loop_state = self.loop_state
        stop_expr = self.stop_expr
        if stop_expr != expand_expr(stop_expr, loop_state):
            return False
        step_expr = self.step_expr
        if step_expr != expand_expr(step_expr, loop_state):
            return False
        return True
