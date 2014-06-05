from soap.common.cache import cached
from soap.expression import operators
from soap.expression.arithmetic import BinaryArithExpr, TernaryArithExpr


class StateGetterExpr(BinaryArithExpr):
    __slots__ = ()

    def __init__(self, a1=None, a2=None, top=False, bottom=False):
        super().__init__(
            operators.STATE_GETTER_OP, a1, a2, top=top, bottom=bottom)

    @property
    def meta_state(self):
        return self.a1

    @property
    def key(self):
        return self.a2

    def eval(self, state):
        raise NotImplementedError(
            'Why would you want to evaluate this expression?')

    def label(self, context=None):
        raise NotImplementedError(
            'Why do you need to find labelling for this expression?')

    def __str__(self):
        return '{meta_state}[{key}]'.format(
            meta_state=self.meta_state, key=self.key)


class LinkExpr(BinaryArithExpr):
    __slots__ = ()

    def __init__(self, a1=None, a2=None, top=False, bottom=False):
        """
        Args:
            a1: target expression
            a2: metastate object for the target expression expansion
        """
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

    def label(self, context=None):
        from soap.label.base import LabelContext
        from soap.semantics.label import LabelSemantics

        context = context or LabelContext(self)

        target_label, target_env = self.target_expr.label(context)
        meta_label, meta_env = self.meta_state.label(context)

        expr = self.__class__(target_label, meta_label)
        label = context.Label(expr)
        env = {
            label: expr,
            target_label: target_env,
            meta_label: meta_env,
        }
        return LabelSemantics(label, env)

    def __str__(self):
        expr, state = self._args_to_str()
        return '{expr} {op} {state}'.format(expr=expr, op=self.op, state=state)


class FixExpr(TernaryArithExpr):
    """Fixpoint expression."""

    def __init__(self, a1=None, a2=None, a3=None, top=False, bottom=False):
        super().__init__(
                operators.FIXPOINT_OP, a1, a2, a3, top=top, bottom=bottom)

    @property
    def bool_expr(self):
        return self.a1

    @property
    def meta_state(self):
        return self.a2

    @property
    def loop_var(self):
        return self.a3

    def _fixpoint(self, state):
        from soap.semantics.state.functions import fixpoint_eval

        fixpoint = fixpoint_eval(
            state, self.bool_expr, loop_meta_state=self.meta_state)
        fixpoint['last_entry']._warn_non_termination(self)
        return fixpoint

    @cached
    def eval(self, state):
        return self._fixpoint(state)['exit'][self.loop_var]

    def label(self, context=None):
        from soap.label.base import LabelContext
        from soap.semantics.label import LabelSemantics

        context = context or LabelContext(self)

        fix_expr_label, env = self.a2.label(context)

        expr = self.__class__(self.a1, fix_expr_label)
        label = context.Label(expr)
        env[label] = expr

        return LabelSemantics(label, env)

    def __str__(self):
        return '{op}(λe.({bool_expr} ? e % {loop_state} : {var}))'.format(
            op=self.op, bool_expr=self.a1, loop_state=self.a2, var=self.a3)
        return '{op}({a1}, {a2}, {a3})'.format(
            op=self.op, a1=self.bool_expr, a2=self.meta_state,
            a3=self.loop_var)
