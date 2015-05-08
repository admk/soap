from soap.common.formatting import underline

from soap.expression.operators import FIXPOINT_OP
from soap.expression.arithmetic import QuaternaryArithExpr


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
