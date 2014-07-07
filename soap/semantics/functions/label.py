import collections

from soap.common import base_dispatcher
from soap.expression import expression_factory
from soap.label import LabelContext
from soap.semantics.label import LabelSemantics


class LabelGenerator(base_dispatcher()):

    def generic_execute(self, expr, context):
        raise TypeError('Do not know how to label {!r}'.format(expr))

    def _execute_atom(self, expr, context):
        label = context.Label(expr)
        env = {label: expr}
        return LabelSemantics(label, env)

    def _execute_expression(self, expr, context):
        semantics_list = tuple(self(arg, context) for arg in expr.args)
        arg_label_list, arg_env_list = zip(*semantics_list)
        expr = expression_factory(expr.op, *arg_label_list)
        label = context.Label(expr)
        label_env = {label: expr}
        for env in arg_env_list:
            label_env.update(env)
        return LabelSemantics(label, label_env)

    def execute_numeral(self, expr, context):
        return self._execute_atom(expr, context)

    def execute_Variable(self, expr, context):
        return self._execute_atom(expr, context)

    def execute_BinaryArithExpr(self, expr, context):
        return self._execute_expression(expr, context)

    def execute_BinaryBoolExpr(self, expr, context):
        return self._execute_expression(expr, context)

    def execute_SelectExpr(self, expr, context):
        return self._execute_expression(expr, context)

    def execute_FixExpr(self, expr, context):
        bool_expr_labsem = self(expr.bool_expr, context)
        bool_expr_label, _ = bool_expr_labsem

        loop_state_label, loop_state_env = self(expr.loop_state, context)
        init_state_label, init_state_env = self(expr.init_state, context)

        label_expr = expr.__class__(
            bool_expr_label, loop_state_label, expr.loop_var, init_state_label)
        label = context.Label(label_expr)

        expr = expr.__class__(
            bool_expr_labsem, loop_state_env, expr.loop_var, init_state_env)
        env = {label: expr}
        return LabelSemantics(label, env)

    def execute_MetaState(self, expr, context):
        from soap.semantics.state.meta import MetaState
        env = {}
        # FIXME better determinism in labelling, currently uses str-based
        # sorting, could use context.out_vars to traverse trees
        for each_var, each_expr in sorted(expr.items(), key=str):
            expr_label, expr_env = self(each_expr, context)
            env.update(expr_env)
            env[each_var] = expr_label
        label = context.Label(MetaState(env))

        return LabelSemantics(label, env)

    def _execute(self, expr, context=None):
        context = context or LabelContext(expr)
        return super()._execute(expr, context)


_label = LabelGenerator()


def label(expr, out_vars, context=None):
    from soap.semantics.state.fusion import fusion
    lab, env = _label(expr, context)
    if isinstance(expr, collections.Mapping):
        env = fusion(env, out_vars)
    return LabelSemantics(lab, env)


def luts(expr, out_vars, exponent, mantissa):
    return label(expr, out_vars).luts(exponent, mantissa)
