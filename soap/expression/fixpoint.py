from soap.common.cache import cached
from soap.common.formatting import underline

from soap.expression.operators import FIXPOINT_OP
from soap.expression.arithmetic import QuaternaryArithExpr


class FixExpr(QuaternaryArithExpr):
    """Fixpoint expression."""

    def __init__(self, a1=None, a2=None, a3=None, a4=None,
                 top=False, bottom=False):
        super().__init__(FIXPOINT_OP, a1, a2, a3, a4, top=top, bottom=bottom)

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

    def _fixpoint(self, state):
        from soap.semantics.state.functions import (
            fixpoint_eval, arith_eval_meta_state
        )
        state = arith_eval_meta_state(state, self.init_state)
        fixpoint = fixpoint_eval(
            state, self.bool_expr, loop_meta_state=self.loop_state)
        fixpoint['last_entry']._warn_non_termination(self)
        return fixpoint

    @cached
    def eval(self, state):
        return self._fixpoint(state)['exit'][self.loop_var]

    def label(self, context=None):
        from soap.label.base import LabelContext
        from soap.semantics.label import LabelSemantics

        context = context or LabelContext(self)

        bool_expr_labsem = self.bool_expr.label(context)
        bool_expr_label, _ = bool_expr_labsem

        loop_state_label, loop_state_env = self.loop_state.label(context)
        init_state_label, init_state_env = self.init_state.label(context)

        label_expr = self.__class__(
            bool_expr_label, loop_state_label, self.loop_var, init_state_label)
        label = context.Label(label_expr)

        expr = self.__class__(
            bool_expr_labsem, loop_state_env, self.loop_var, init_state_env)
        env = {label: expr}
        return LabelSemantics(label, env)

    def __str__(self):
        fixpoint_var = underline('e')
        s = ('{op}(λ{fvar}.({bool_expr} ? {fvar} % {loop_state} : {var}))'
             ' % {init_state}')
        return s.format(
            fvar=fixpoint_var, op=self.op, bool_expr=self.bool_expr,
            loop_state=self.loop_state, var=self.loop_var,
            init_state=self.init_state)
