from soap.common.cache import cached
from soap.expression import operators
from soap.expression.arithmetic import BinaryArithExpr


class LinkExpr(BinaryArithExpr):
    __slots__ = ()

    def __init__(self, a1=None, a2=None, top=False, bottom=False):
        super().__init__(operators.LINK_OP, a1, a2, top=top, bottom=bottom)

    @property
    def target_expr(self):
        return self.a1

    @property
    def meta_state(self):
        return self.a2

    @cached
    def eval(self, state):
        from soap.semantics.state.functions import (
            arith_eval, arith_eval_meta_state
        )
        state = arith_eval_meta_state(state, self.meta_state)
        return arith_eval(state, self.target_expr)

    def __str__(self):
        expr, state = self._args_to_str()
        return '{expr} % {state}'.format(expr=expr, state=state)

    def __repr__(self):
        return '{cls}({a1!r}, {a2!r})'.format(
            cls=self.__class__.__name__, a1=self.a1, a2=self.a2)


class FixExpr(BinaryArithExpr):
    """Fixpoint expression."""

    def __init__(self, a1=None, a2=None, top=False, bottom=False):
        super().__init__(operators.FIXPOINT_OP, a1, a2, top=top, bottom=bottom)

    @property
    def fix_var(self):
        return self.a1

    @property
    def fix_expr(self):
        return self.a2

    def _fixpoint(self, state):
        from soap.semantics.state.functions import fixpoint_eval

        fix_expr = self.fix_expr
        bool_expr = fix_expr.bool_expr
        loop_meta_state = fix_expr.true_expr.meta_state

        fixpoint = fixpoint_eval(
            state, bool_expr, loop_meta_state=loop_meta_state)
        fixpoint['last_entry']._warn_non_termination(self)
        return fixpoint

    @cached
    def eval(self, state):
        return self._fixpoint(state)['exit'][self.fix_expr.false_expr]

    def __str__(self):
        return '{op}[{a1} ↦ {a2}]'.format(op=self.op, a1=self.a1, a2=self.a2)
