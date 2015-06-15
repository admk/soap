import collections

from soap.common import base_dispatcher, cached
from soap.expression import operators, BinaryBoolExpr, Subscript
from soap.semantics.error import error_norm
from soap.semantics.linalg import ErrorSemanticsArray


_unary_operator_function_dictionary = {
    operators.UNARY_SUBTRACT_OP: lambda x: -x,
    operators.EXPONENTIATE_OP: lambda x: x.exp(),
}
_binary_operator_function_dictionary = {
    operators.ADD_OP: lambda x, y: x + y,
    operators.SUBTRACT_OP: lambda x, y: x - y,
    operators.MULTIPLY_OP: lambda x, y: x * y,
    operators.DIVIDE_OP: lambda x, y: x / y,
    operators.BARRIER_OP: lambda x, y: error_norm([x, y]),
}


class ArithmeticEvaluator(base_dispatcher()):

    def generic_execute(self, expr, state):
        raise TypeError('Do not know how to evaluate {!r}'.format(expr))

    def execute_numeral(self, expr, state):
        return expr

    def execute_PartitionLabel(self, expr, state):
        return expr.bound

    def _execute_args(self, expr, state):
        return tuple(self(arg, state) for arg in expr.args)

    def execute_Variable(self, expr, state):
        return state[expr]

    def execute_UnaryArithExpr(self, expr, state):
        a, = self._execute_args(expr, state)
        try:
            op = _unary_operator_function_dictionary[expr.op]
        except KeyError:
            raise KeyError('Unrecognized operator type {!r}'.format(op))
        return op(a)

    def execute_BinaryArithExpr(self, expr, state):
        a1, a2 = self._execute_args(expr, state)
        try:
            op = _binary_operator_function_dictionary[expr.op]
        except KeyError:
            raise KeyError('Unrecognized operator type {!r}'.format(self.op))
        return op(a1, a2)

    execute_Subscript = _execute_args

    def execute_AccessExpr(self, expr, state):
        array, subscript = self._execute_args(expr, state)
        if array.is_bottom():
            return array.value_class(bottom=True)
        return array[subscript]

    def execute_UpdateExpr(self, expr, state):
        array, subscript, value = self._execute_args(expr, state)
        if array.is_bottom():
            return array
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
        from soap.semantics.functions.fixpoint import fix_expr_eval
        return fix_expr_eval(expr, state)

    def execute_MetaState(self, meta_state, state):
        return state.__class__({
            var: self(expr, state) for var, expr in meta_state.items()})

    @cached
    def __call__(self, expr, state):
        return super().__call__(expr, state)

    def __eq__(self, other):
        return self.__class__ == other.__class__

    def __hash__(self):
        return hash(self.__class__)


arith_eval = ArithmeticEvaluator()


def error_eval(expr, state, to_norm=True):
    if isinstance(expr, (BinaryBoolExpr, Subscript)):
        return 0
    value = arith_eval(expr, state)
    if not to_norm:
        return value
    if isinstance(value, ErrorSemanticsArray):
        value = error_norm(value._flat_items)
    elif isinstance(value, collections.Mapping):
        value = error_norm(value.values())
    return value
