from soap.common import base_dispatcher, cached
from soap.expression import operators
from soap.semantics.error import ErrorSemantics, FloatInterval, error_norm


class ArithmeticEvaluator(base_dispatcher()):

    _unary_operator_function_dictionary = {
        operators.UNARY_SUBTRACT_OP: lambda x: -x,
    }

    _binary_operator_function_dictionary = {
        operators.ADD_OP: lambda x, y: x + y,
        operators.SUBTRACT_OP: lambda x, y: x - y,
        operators.MULTIPLY_OP: lambda x, y: x * y,
        operators.DIVIDE_OP: lambda x, y: x / y,
        operators.BARRIER_OP: lambda x, y: error_norm([x, y]),
    }

    def generic_execute(self, expr, state):
        raise TypeError('Do not know how to evaluate {!r}'.format(expr))

    def execute_numeral(self, expr, state):
        return expr

    def _execute_args(self, expr, state):
        return tuple(self(arg, state) for arg in expr.args)

    def execute_Variable(self, expr, state):
        return state[expr]

    def execute_UnaryArithExpr(self, expr, state):
        a, = self._execute_args(expr, state)
        try:
            op = self._unary_operator_function_dictionary[expr.op]
        except KeyError:
            raise KeyError('Unrecognized operator type {!r}'.format(op))
        return op(a)

    def execute_BinaryArithExpr(self, expr, state):
        a1, a2 = self._execute_args(expr, state)
        try:
            op = self._binary_operator_function_dictionary[expr.op]
        except KeyError:
            raise KeyError('Unrecognized operator type {!r}'.format(self.op))
        return op(a1, a2)

    execute_Subscript = _execute_args

    def execute_AccessExpr(self, expr, state):
        array, subscript = self._execute_args(expr, state)
        return array[subscript]

    def execute_UpdateExpr(self, expr, state):
        array, subscript, value = self._execute_args(expr, state)
        return array.update(subscript, value)

    def execute_SelectExpr(self, expr, state):
        from soap.semantics.functions.boolean import bool_eval
        eval_split = lambda split_expr, split_state: self(
            split_expr, split_state)
        true_state, false_state = bool_eval(expr.bool_expr, state)
        true_value = eval_split(expr.true_expr, true_state)
        false_value = eval_split(expr.false_expr, false_state)
        return true_value | false_value

    def execute_FixExpr(self, expr, state):
        from soap.semantics.functions import fix_expr_eval
        return fix_expr_eval(expr, state)

    def execute_UnrollExpr(self, expr, state):
        from soap.semantics.functions import unroll_eval
        expr, kernel, depth = expr.args
        return unroll_eval(expr, kernel, state, depth)

    def execute_MetaState(self, meta_state, state):
        from soap.semantics.functions import arith_eval_meta_state
        return arith_eval_meta_state(meta_state, state)

    @cached
    def __call__(self, expr, state):
        return super().__call__(expr, state)

    def __eq__(self, other):
        return self.__class__ == other.__class__

    def __hash__(self):
        return hash('arith_eval')


arith_eval = ArithmeticEvaluator()


class ErrorEvaluator(ArithmeticEvaluator):

    def execute_Variable(self, expr, state):
        value = state[expr]
        if isinstance(value, FloatInterval):
            value = ErrorSemantics(value, 0)
        return value

    def execute_BinaryBoolExpr(self, expr, state):
        return 0

    def execute_MetaState(self, meta_state, state):
        return error_norm([self(expr, state) for expr in meta_state.values()])


error_eval = ErrorEvaluator()
