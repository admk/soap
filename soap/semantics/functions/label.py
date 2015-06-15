import collections

from soap.common import base_dispatcher, cached
from soap.expression import expression_factory, operators
from soap.semantics.functions import error_eval
from soap.semantics.label import LabelContext, LabelSemantics
from soap.semantics.linalg import IntegerIntervalArray


class LabelGenerator(base_dispatcher()):
    def __init__(self, context):
        super().__init__()
        self.context = context

    def Label(self, expr, bound, invar):
        return self.context.Label(expr, bound, invar)

    def generic_execute(self, expr, state):
        raise TypeError('Do not know how to label {!r}'.format(expr))

    def execute_PartitionLabel(self, expr, state):
        return LabelSemantics(expr, {})

    def _execute_atom(self, expr, state):
        bound = error_eval(expr, state, to_norm=False)
        label = self.Label(expr, bound, None)
        env = {label: expr}
        return LabelSemantics(label, env)

    execute_numeral = execute_Variable = _execute_atom

    def _execute_expression(self, expr, state):
        semantics_list = tuple(self(arg, state) for arg in expr.args)
        arg_label_list, arg_env_list = zip(*semantics_list)
        label_expr = expression_factory(expr.op, *arg_label_list)
        label_env = {}
        for env in arg_env_list:
            label_env.update(env)
        return label_expr, label_env

    def _execute_arithmetic_expression(self, expr, state):
        label_expr, label_env = self._execute_expression(expr, state)
        bound = error_eval(expr, state, to_norm=False)
        label = self.Label(expr, bound, None)
        label_env[label] = label_expr
        return LabelSemantics(label, label_env)

    execute_UnaryArithExpr = _execute_arithmetic_expression
    execute_BinaryArithExpr = _execute_arithmetic_expression
    execute_SelectExpr = _execute_arithmetic_expression

    def execute_BinaryBoolExpr(self, expr, state):
        label_expr, label_env = self._execute_expression(expr, state)
        sub_expr = expression_factory(operators.SUBTRACT_OP, expr.a1, expr.a2)
        bound = error_eval(sub_expr, state, to_norm=False)
        label = self.Label(expr, bound, None)
        label_env[label] = label_expr
        return LabelSemantics(label, label_env)

    def execute_Subscript(self, expr, state):
        label_expr, label_env = self._execute_expression(expr, state)
        bound = IntegerIntervalArray([b.bound for b in label_expr.args])
        label = self.Label(expr, bound, None)
        label_env[label] = label_expr
        return LabelSemantics(label, label_env)

    execute_AccessExpr = execute_UpdateExpr = _execute_arithmetic_expression

    def execute_FixExpr(self, expr, state):
        from soap.semantics.functions import fixpoint_eval

        bool_expr = expr.bool_expr
        loop_var = expr.loop_var

        init_labsem = self(expr.init_state, state)
        init_label, init_env = init_labsem

        loop_state = expr.loop_state
        loop_info = fixpoint_eval(init_label.bound, bool_expr, loop_state)
        loop_labsem = self(loop_state, loop_info['entry'])
        loop_label, loop_env = loop_labsem

        bool_labsem = self(bool_expr, loop_info['end'])
        bool_label, _ = bool_labsem

        loop_var_bound = loop_info['exit'][loop_var]
        label = self.Label(expr, loop_var_bound, loop_info['entry'])

        expr = expr.__class__(bool_labsem, loop_env, loop_var, init_env)
        env = {label: expr}
        return LabelSemantics(label, env)

    def execute_MetaState(self, expr, state):
        env = {}
        for each_var, each_expr in sorted(expr.items(), key=str):
            expr_label, expr_env = self(each_expr, state)
            env.update(expr_env)
            env[each_var] = expr_label

        bound = error_eval(expr, state, to_norm=False)
        label = self.Label(expr, bound, None)
        return LabelSemantics(label, env)

    @cached
    def __call__(self, expr, state=None):
        return super().__call__(expr, state)

    execute = __call__


@cached
def label(expr, state, out_vars, context=None, fusion=True):
    from soap.semantics.state import BoxState, MetaState
    state = state or BoxState(bottom=True)
    context = context or LabelContext(expr)

    if isinstance(expr, collections.Mapping):
        out_vars = out_vars or expr.keys()
        expr = MetaState({k: v for k, v in expr.items() if k in out_vars})

    lab, env = LabelGenerator(context).execute(expr, state)

    if fusion and isinstance(expr, collections.Mapping):
        from soap.semantics.state.fusion import fusion
        env = fusion(env, out_vars)

    return LabelSemantics(lab, env)


@cached
def resource_eval(expr, state, out_vars):
    return label(expr, state, out_vars).resources()


def luts(expr, state, out_vars):
    return resource_eval(expr, state, out_vars).lut
