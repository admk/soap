import collections

from soap.common import base_dispatcher, cached
from soap.context import context
from soap.expression import expression_factory, operators
from soap.semantics.functions import error_eval
from soap.semantics.label import LabelContext, LabelSemantics


class LabelGenerator(base_dispatcher()):

    def generic_execute(self, expr, state, context):
        raise TypeError('Do not know how to label {!r}'.format(expr))

    def _execute_atom(self, expr, state, context):
        bound = error_eval(expr, state)
        label = context.Label(expr, bound)
        env = {label: expr}
        return LabelSemantics(label, env)

    execute_numeral = execute_Variable = _execute_atom

    def _execute_expression(self, expr, state, context):
        semantics_list = tuple(self(arg, state, context) for arg in expr.args)
        arg_label_list, arg_env_list = zip(*semantics_list)
        label_expr = expression_factory(expr.op, *arg_label_list)
        label_env = {}
        for env in arg_env_list:
            label_env.update(env)
        return label_expr, label_env

    def _execute_arithmetic_expression(self, expr, state, context):
        label_expr, label_env = self._execute_expression(expr, state, context)
        bound = error_eval(expr, state)
        label = context.Label(label_expr, bound)
        label_env[label] = label_expr
        return LabelSemantics(label, label_env)

    execute_UnaryArithExpr = _execute_arithmetic_expression
    execute_BinaryArithExpr = _execute_arithmetic_expression
    execute_SelectExpr = _execute_arithmetic_expression

    def execute_BinaryBoolExpr(self, expr, state, context):
        label_expr, label_env = self._execute_expression(expr, state, context)
        sub_expr = expression_factory(operators.SUBTRACT_OP, expr.a1, expr.a2)
        bound = error_eval(sub_expr, state)
        label = context.Label(label_expr, bound)
        label_env[label] = label_expr
        return LabelSemantics(label, label_env)

    def execute_FixExpr(self, expr, state, context):
        from soap.semantics.functions import (
            arith_eval_meta_state, fixpoint_eval
        )

        init_state = expr.init_state
        loop_state = expr.loop_state
        bool_expr = expr.bool_expr

        init_bound = arith_eval_meta_state(init_state, state)
        init_state_label, init_state_env = self(init_state, state, context)

        loop_bound = fixpoint_eval(init_bound, bool_expr, loop_state)['entry']
        loop_state_labsem = self(loop_state, loop_bound, context)
        loop_state_label, loop_state_env = loop_state_labsem

        bool_expr_labsem = self(bool_expr, loop_bound, context)
        bool_expr_label, _ = bool_expr_labsem

        label_expr = expr.__class__(
            bool_expr_label, loop_state_label, expr.loop_var, init_state_label)
        label = context.Label(label_expr, None)

        expr = expr.__class__(
            bool_expr_labsem, loop_state_env, expr.loop_var, init_state_env)
        env = {label: expr}
        return LabelSemantics(label, env)

    def execute_MetaState(self, expr, state, context):
        from soap.semantics.state.meta import MetaState
        env = {}
        for each_var, each_expr in sorted(expr.items(), key=hash):
            expr_label, expr_env = self(each_expr, state, context)
            env.update(expr_env)
            env[each_var] = expr_label
        label = context.Label(MetaState(env), None)

        return LabelSemantics(label, env)

    @cached
    def __call__(self, expr, state, context=None):
        context = context or LabelContext(expr)
        return super().__call__(expr, state, context)


_label = LabelGenerator()


def label(expr, state, out_vars, context=None):
    from soap.semantics.state.meta import MetaState
    if isinstance(expr, MetaState):
        expr = MetaState({k: v for k, v in expr.items() if k in out_vars})
    lab, env = _label(expr, state, context)
    if isinstance(expr, collections.Mapping):
        from soap.semantics.state.fusion import fusion
        env = fusion(env, out_vars)
    return LabelSemantics(lab, env)


_luts_context = LabelContext('luts_count')


@cached
def luts(expr, state, out_vars, mantissa=None):
    mantissa = mantissa or context.precision
    return label(expr, state, out_vars, _luts_context).luts(mantissa)
