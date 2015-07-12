"""
.. module:: soap.expression.common
    :synopsis: Common definitions for expressions.
"""
from soap.common.base import base_dispatcher
from soap.common.cache import cached


def is_variable(e):
    from soap.expression.variable import Variable
    return isinstance(e, Variable)


def is_variable_tuple(e):
    from soap.expression.variable import VariableTuple
    return isinstance(e, VariableTuple)


def is_expression(e):
    from soap.expression.base import Expression
    from soap.expression.variable import Variable, VariableTuple
    if not isinstance(e, Expression):
        return False
    if isinstance(e, Variable):
        return False
    if isinstance(e, VariableTuple):
        return False
    return True


def is_arith_expr(e):
    """Check if `e` is an expression."""
    from soap.expression.arithmetic import ArithExpr
    return isinstance(e, ArithExpr)


def is_bool_expr(e):
    """Check if `e` is a boolean expression."""
    from soap.expression.boolean import BoolExpr
    return isinstance(e, BoolExpr)


def concat_multi_expr(*expr_args):
    """Concatenates multiple expressions into a single expression by using the
    barrier operator.
    """
    me = None
    for e in expr_args:
        me = me | e if me else e
    return me


def split_multi_expr(e):
    """Splits the single expression into multiple expressions."""
    from soap.expression.operators import BARRIER_OP
    if e.op != BARRIER_OP:
        return [e]
    return split_multi_expr(e.a1) + split_multi_expr(e.a2)


op_expr_cls_map = None


@cached
def expression_factory(op, *args):
    from soap.expression import operators
    from soap.expression.arithmetic import (
        UnaryArithExpr, BinaryArithExpr, TernaryArithExpr, SelectExpr
    )
    from soap.expression.boolean import (
        UnaryBoolExpr, BinaryBoolExpr, TernaryBoolExpr
    )
    from soap.expression.fixpoint import FixExpr
    from soap.expression.linalg import Subscript, AccessExpr, UpdateExpr

    global op_expr_cls_map
    if not op_expr_cls_map:
        op_expr_cls_map = {
            operators.SUBSCRIPT_OP: Subscript,
            operators.INDEX_ACCESS_OP: AccessExpr,
            operators.INDEX_UPDATE_OP: UpdateExpr,
            operators.FIXPOINT_OP: FixExpr,
            operators.TERNARY_SELECT_OP: SelectExpr,
        }
    cls = op_expr_cls_map.get(op)
    if cls:
        return cls(*args)

    if op in operators.ARITHMETIC_OPERATORS:
        class_list = [UnaryArithExpr, BinaryArithExpr, TernaryArithExpr]
    elif op in operators.BOOLEAN_OPERATORS:
        class_list = [UnaryBoolExpr, BinaryBoolExpr, TernaryBoolExpr]
    else:
        raise ValueError('Unknown operator {}.'.format(op))
    try:
        cls = class_list[len(args) - 1]
    except IndexError:
        raise ValueError('Too many arguments.')
    return cls(op, *args)


class GenericExecuter(base_dispatcher()):
    def __init__(self, *arg, **kwargs):
        super().__init__()

        for attr in ['numeral', 'Variable']:
            self._set_default_method(attr, self._execute_atom)

        expr_cls_list = [
            'UnaryArithExpr', 'BinaryArithExpr', 'UnaryBoolExpr',
            'BinaryBoolExpr', 'AccessExpr', 'UpdateExpr', 'SelectExpr',
            'Subscript', 'FixExpr',
        ]
        for attr in expr_cls_list:
            self._set_default_method(attr, self._execute_expression)

        self._set_default_method('MetaState', self._execute_mapping)

    def _set_default_method(self, name, value):
        name = 'execute_{}'.format(name)
        if hasattr(self, name):
            return
        setattr(self, name, value)

    def generic_execute(self, expr, *args, **kwargs):
        raise TypeError('Do not know how to execute {!r}'.format(expr))

    def _execute_atom(self, expr, *args, **kwargs):
        raise NotImplementedError

    def _execute_expression(self, expr, *args, **kwargs):
        raise NotImplementedError

    def _execute_mapping(self, meta_state, *args, **kwargs):
        raise NotImplementedError


class VariableSetGenerator(GenericExecuter):
    def generic_execute(self, expr):
        raise TypeError(
            'Do not know how to find input variables for {!r}'.format(expr))

    def _execute_atom(self, expr):
        return {expr}

    def _execute_expression(self, expr):
        input_vars = set()
        for arg in expr.args:
            input_vars |= self(arg)
        return input_vars

    def execute_tuple(self, expr):
        return set(expr)

    def execute_numeral(self, expr):
        return set()

    def execute_FixExpr(self, expr):
        input_vars = set()
        for expr in expr.init_state.values():
            input_vars |= self(expr)
        return input_vars


expression_variables = VariableSetGenerator()


class HasInnerLoop(GenericExecuter):
    def generic_execute(self, expr):
        raise TypeError(
            'Do not know how to find inner loops in {!r}'.format(expr))

    def _execute_atom(self, expr):
        return False

    def _execute_expression(self, expr):
        return any(self(arg) for arg in expr.args)

    def execute_FixExpr(self, expr):
        return True

    def _execute_mapping(self, expr):
        return any(self(var_expr) for var_expr in expr.values())


_has_inner_loop = HasInnerLoop()


def fix_expr_has_inner_loop(expr):
    return _has_inner_loop(expr.loop_state)
