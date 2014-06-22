from soap.common import base_dispatcher
from soap.expression import operators


class ArithmeticEvaluator(base_dispatcher()):

    _unary_operator_function_dictionary = {
        operators.UNARY_SUBTRACT_OP: lambda x, _: -x,
    }

    _binary_operator_function_dictionary = {
        operators.ADD_OP: lambda x, y: x + y,
        operators.SUBTRACT_OP: lambda x, y: x - y,
        operators.MULTIPLY_OP: lambda x, y: x * y,
        operators.DIVIDE_OP: lambda x, y: x / y,
    }

    _binary_boolean_operator_function_dictionary = {
        operators.LESS_OP: lambda x, y: x < y,
        operators.LESS_EQUAL_OP: lambda x, y: x <= y,
        operators.EQUAL_OP: lambda x, y: x == y,
        operators.GREATER_EQUAL_OP: lambda x, y: x >= y,
        operators.GREATER_OP: lambda x, y: x > y,
    }

    def generic_execute(self, expr, state):
        raise TypeError('Do not know how to evaluate {!r}'.format(expr))

    def execute_numeral(self, expr, state):
        return expr

    def _execute_args(self, args, state):
        return tuple(self(arg, state) for arg in args)

    def execute_Variable(self, expr, state):
        return state[expr]

    def execute_UnaryArithExpr(self, expr, state):
        a, = self._execute_args(expr.args, state)
        try:
            op = self._unary_operator_function_dictionary[expr.op]
        except KeyError:
            raise KeyError('Unrecognized operator type {!r}'.format(op))
        return op(a)

    def execute_BinaryArithExpr(self, expr, state):
        a1, a2 = self._execute_args(expr.args, state)
        try:
            op = self._binary_operator_function_dictionary[expr.op]
        except KeyError:
            raise KeyError('Unrecognized operator type {!r}'.format(self.op))
        return op(a1, a2)

    def execute_SelectExpr(self, expr, state):
        from soap.semantics.functions.boolean import bool_eval
        eval_split = lambda split_expr, split_state: self(
            split_expr, split_state)
        true_state, false_state = bool_eval(expr.bool_expr, state)
        true_value = eval_split(expr.true_expr, true_state)
        false_value = eval_split(expr.false_expr, false_state)
        return true_value | false_value

    def execute_BinaryBoolExpr(self, expr, state):
        a1, a2 = self._execute_args(expr.args, state)
        try:
            op = self._binary_boolean_operator_function_dictionary[expr.op]
        except KeyError:
            raise KeyError('Unrecognized operator type {!r}'.format(self.op))
        return op(a1, a2)

    def execute_FixExpr(self, expr, state):
        from soap.semantics.functions.fixpoint import (
            fixpoint_eval, arith_eval_meta_state
        )
        state = arith_eval_meta_state(state, expr.init_state)
        fixpoint = fixpoint_eval(
            state, expr.bool_expr, loop_meta_state=expr.loop_state)
        fixpoint['last_entry']._warn_non_termination(expr)
        return fixpoint['exit'][expr.loop_var]

    def execute_MetaState(self, meta_state, state):
        error = None
        for expr in meta_state.values():
            expr_error = self(expr, state)
            if not error:
                error = expr_error
            else:
                error |= expr_error
        return error


arith_eval = ArithmeticEvaluator()


def error_eval(expr, state, prec=None):
    # TODO rework prec
    from soap.semantics import (
        precision_context, BoxState, FloatInterval, ErrorSemantics
    )
    with precision_context(prec):
        new_state = {}
        for key, value in state.items():
            if isinstance(value, FloatInterval):
                value = ErrorSemantics(value, 0)
            new_state[key] = value
        new_state = BoxState(new_state)
        return ErrorSemantics(arith_eval(expr, new_state))
