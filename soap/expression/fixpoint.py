from soap.common.cache import cached
from soap.expression import operators
from soap.expression.common import expression_factory
from soap.expression.arithmetic import BinaryArithExpr, TernaryArithExpr


class LinkExpr(TernaryArithExpr):
    __slots__ = ()

    def __init__(self, a1=None, a2=None, a3=None, top=False, bottom=False):
        """
        Args:
            a1: target expression
            a2: metastate object for the target expression expansion
            a3: label for identification throughout transformations
        """
        super().__init__(operators.LINK_OP, a1, a2, a3, top=top, bottom=bottom)

    @property
    def target_expr(self):
        return self.a1

    @property
    def meta_state(self):
        return self.a2

    @property
    def label_of_equivalence(self):
        return self.a3

    @cached
    def eval(self, state):
        from soap.semantics.state.functions import (
            arith_eval, arith_eval_meta_state
        )
        state = arith_eval_meta_state(state, self.meta_state)
        return arith_eval(state, self.target_expr)

    @cached
    def label(self):
        from soap.label.base import Label
        from soap.semantics.label import LabelSemantics

        target_label, target_env = self.target_expr.label()

        meta_state = self.meta_state
        meta_label = Label(meta_state)
        meta_env = {}
        for var, expr in meta_state.items():
            expr_label, expr_env = expr.label()
            meta_env.update(expr_env)
            meta_env[var] = expr_label

        expr = expression_factory(
            self.op, target_label, meta_label, self.label_of_equivalence)

        label = Label(expr)
        env = {
            label: expr,
            target_label: target_env,
            meta_label: meta_env,
        }
        return LabelSemantics(label, env)

    def __str__(self):
        expr, state, eq_label = self._args_to_str()
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
