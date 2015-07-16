import collections

from soap.common import base_dispatcher, cached
from soap.datatype import type_cast
from soap.expression import expression_factory
from soap.semantics.error import _coerce
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

    def _execute_atom(self, expr, bound):
        label = self.Label(expr, bound, None)
        env = {label: expr}
        return LabelSemantics(label, env)

    def execute_numeral(self, expr, state):
        return self._execute_atom(expr, expr)

    def execute_Variable(self, expr, state):
        if state is not None:
            bound = error_eval(expr, state, to_norm=False)
        else:
            bound = type_cast(expr.dtype, bottom=True)
        return self._execute_atom(expr, bound)

    def _execute_expression(self, expr, state, bound_func):
        semantics_list = tuple(self(arg, state) for arg in expr.args)
        arg_label_list, arg_env_list = zip(*semantics_list)
        label_expr = expression_factory(expr.op, *arg_label_list)
        label_env = {}
        for env in arg_env_list:
            label_env.update(env)
        if state is not None:
            bound = error_eval(expr, state, to_norm=False)
        else:
            bound = bound_func(label_expr)
        label = self.Label(expr, bound, None)
        label_env[label] = label_expr
        return LabelSemantics(label, label_env)

    def _execute_binary_expression(self, expr, state):
        def bound_func(label_expr):
            a1, a2 = label_expr.args
            return _coerce(a1.bound, a2.bound)(bottom=True)
        return self._execute_expression(expr, state, bound_func)

    def execute_UnaryArithExpr(self, expr, state):
        def bound_func(label_expr):
            return label_expr.args[0].bound
        return self._execute_expression(expr, state, bound_func)

    execute_BinaryArithExpr = _execute_binary_expression

    def execute_SelectExpr(self, expr, state):
        def bound_func(label_expr):
            _, a1, a2 = label_expr.args
            return _coerce(a1.bound, a2.bound)(bottom=True)
        return self._execute_expression(expr, state, bound_func)

    execute_BinaryBoolExpr = _execute_binary_expression

    def execute_Subscript(self, expr, state):
        def bound_func(label_expr):
            args = tuple(b.bound for b in label_expr.args)
            return IntegerIntervalArray(args)
        return self._execute_expression(expr, state, bound_func)

    def execute_AccessExpr(self, expr, state):
        def bound_func(label_expr):
            dtype = label_expr.var.dtype.num_type
            return type_cast(dtype, bottom=True)
        return self._execute_expression(expr, state, bound_func)

    def execute_UpdateExpr(self, expr, state):
        def bound_func(label_expr):
            dtype = label_expr.var.dtype
            return type_cast(dtype, bottom=True)
        return self._execute_expression(expr, state, bound_func)

    def execute_FixExpr(self, expr, state):
        from soap.semantics.error import IntegerInterval
        from soap.semantics.functions import fixpoint_eval
        from soap.semantics.state import BoxState

        bool_expr = expr.bool_expr
        loop_var = expr.loop_var

        init_labsem = self(expr.init_state, state)
        init_label, init_env = init_labsem

        if state is not None:
            loop_info = fixpoint_eval(expr, init_label.bound)
            loop_var_bound = loop_info['exit'][loop_var]
        else:
            empty = BoxState(bottom=True)
            loop_info = {
                'entry': empty,
                'exit': empty,
                'last_entry': empty,
                'last_exit': empty,
                'end': empty,
                'trip_count': IntegerInterval(bottom=True),
            }
            loop_var_bound = type_cast(loop_var.dtype, bottom=True)

        loop_entry = loop_info['entry']
        if loop_entry.is_bottom():
            loop_entry = None
        loop_labsem = self(expr.loop_state, loop_entry)
        loop_label, loop_env = loop_labsem

        bool_labsem = self(bool_expr, loop_info['end'])
        bool_label, _ = bool_labsem

        label = self.Label(expr, loop_var_bound, loop_info['entry'])

        expr = expr.__class__(bool_labsem, loop_env, loop_var, init_env)
        env = {label: expr}
        return LabelSemantics(label, env)

    def execute_MetaState(self, expr, state):
        from soap.semantics.state import BoxState
        env = {}
        for each_var, each_expr in sorted(expr.items(), key=str):
            expr_label, expr_env = self(each_expr, state)
            env.update(expr_env)
            env[each_var] = expr_label

        if state is not None:
            bound = error_eval(expr, state, to_norm=False)
        else:
            bound = BoxState(bottom=True)
        label = self.Label(expr, bound, None)
        return LabelSemantics(label, env)

    @cached
    def __call__(self, expr, state=None):
        return super().__call__(expr, state)

    execute = __call__


@cached
def label(expr, state, out_vars, context=None, fusion=True):
    from soap.semantics.state import MetaState

    if state is not None:
        if state and state.is_bottom():
            state = None

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
