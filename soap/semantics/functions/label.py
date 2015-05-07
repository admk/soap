import collections

from soap.common import base_dispatcher, cached
from soap.context import context as global_context
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

    def _execute_atom(self, expr, state):
        bound = error_eval(expr, state, preserve_array=True)
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
        bound = error_eval(expr, state, preserve_array=True)
        label = self.Label(label_expr, bound, None)
        label_env[label] = label_expr
        return LabelSemantics(label, label_env)

    execute_UnaryArithExpr = _execute_arithmetic_expression
    execute_BinaryArithExpr = _execute_arithmetic_expression
    execute_SelectExpr = _execute_arithmetic_expression

    def execute_BinaryBoolExpr(self, expr, state):
        label_expr, label_env = self._execute_expression(expr, state)
        sub_expr = expression_factory(operators.SUBTRACT_OP, expr.a1, expr.a2)
        bound = error_eval(sub_expr, state, preserve_array=True)
        label = self.Label(label_expr, bound, None)
        label_env[label] = label_expr
        return LabelSemantics(label, label_env)

    def execute_Subscript(self, expr, state):
        label_expr, label_env = self._execute_expression(expr, state)
        bound = IntegerIntervalArray([b.bound for b in label_expr.args])
        label = self.Label(label_expr, bound, None)
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

        label_expr = expr.__class__(
            bool_label, loop_label, loop_var, init_label)
        loop_var_bound = loop_info['exit'][loop_var]
        label = self.Label(label_expr, loop_var_bound, loop_info['entry'])

        expr = expr.__class__(bool_labsem, loop_env, loop_var, init_env)
        env = {label: expr}
        return LabelSemantics(label, env)

    def execute_ForExpr(self, expr, state):
        from soap.semantics.functions import fixpoint_eval, expand_expr

        iter_var = expr.iter_var
        start = expr.start_expr
        stop = expr.stop_expr
        step = expr.step_expr
        loop_var = expr.loop_var

        init_labsem = self(expr.init_state, state)
        init_label, init_env = init_labsem

        start_labsem = self(start, init_label.bound)
        start_label, _ = start_labsem

        loop_init_state = init_label.bound.immu_update(
            iter_var, start_label.bound)
        bool_expr = expression_factory(operators.LESS_OP, expr.iter_var, stop)
        loop_state = expr.loop_state
        incr_expr = expression_factory(operators.ADD_OP, expr.iter_var, step)
        incr_expr = expand_expr(incr_expr, loop_state)
        loop_incr_state = loop_state.immu_update(iter_var, incr_expr)
        loop_info = fixpoint_eval(loop_init_state, bool_expr, loop_incr_state)
        loop_labsem = self(loop_state, loop_info['entry'])
        loop_label, loop_env = loop_labsem

        step_labsem = self(step, loop_info['end'])
        step_label, _ = step_labsem
        stop_labsem = self(stop, loop_info['end'])
        stop_label, _ = stop_labsem

        label_expr = expr.__class__(
            iter_var, start_label, stop_label, step_label, loop_label,
            loop_var, init_label)

        loop_var_bound = loop_info['exit'][loop_var]
        label = self.Label(label_expr, loop_var_bound, loop_info['entry'])

        expr = expr.__class__(
            iter_var, start_labsem, stop_labsem, step_labsem,
            loop_env, loop_var, init_env)
        env = {label: expr}
        return LabelSemantics(label, env)

    def execute_UnrollExpr(self, expr, state):
        return self(expr.a1, state)

    def execute_MetaState(self, expr, state):
        from soap.semantics.state.meta import MetaState
        from soap.semantics.functions import arith_eval_meta_state
        env = {}
        for each_var, each_expr in sorted(expr.items(), key=hash):
            expr_label, expr_env = self(each_expr, state)
            env.update(expr_env)
            env[each_var] = expr_label

        bound = arith_eval_meta_state(expr, state)
        label = self.Label(MetaState(env), bound, None)
        return LabelSemantics(label, env)

    @cached
    def __call__(self, expr, state=None):
        return super().__call__(expr, state)

    execute = __call__


@cached
def label(expr, state, out_vars, context=None, fusion=True):
    from soap.semantics.state.meta import MetaState
    if isinstance(expr, MetaState):
        expr = MetaState({k: v for k, v in expr.items() if k in out_vars})
    context = context or LabelContext(expr)
    lab, env = LabelGenerator(context).execute(expr, state)
    if fusion and isinstance(expr, collections.Mapping):
        from soap.semantics.state.fusion import fusion
        env = fusion(env, out_vars)
    return LabelSemantics(lab, env)


@cached
def resource_eval(expr, state, out_vars, mantissa=None):
    mantissa = mantissa or global_context.precision
    return label(expr, state, out_vars).resources(mantissa)


def luts(expr, state, out_vars, mantissa=None):
    return resource_eval(expr, state, out_vars, mantissa).lut
