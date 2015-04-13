import unittest

from soap.datatype import int_type, real_type, IntegerArrayType
from soap.expression import (
    operators, UnaryArithExpr, BinaryArithExpr, SelectExpr,
    FixExpr, AccessExpr, UpdateExpr, BinaryBoolExpr, Variable,
)
from soap.semantics.error import IntegerInterval, ErrorSemantics
from soap.semantics.functions.arithmetic import arith_eval
from soap.semantics.linalg import IntegerIntervalArray
from soap.semantics.state.box import BoxState
from soap.semantics.state.meta import MetaState


class TestArithmeticEvaluator(unittest.TestCase):
    def setUp(self):
        self.a = Variable('a', IntegerArrayType([2, 2]))
        self.x = Variable('x', int_type)
        self.y = Variable('y', int_type)
        self.z = Variable('z', real_type)
        self.state = BoxState(x=[1, 2], y=3, z=[1.0, 2.0])
        self.array_state = BoxState(
            a=IntegerIntervalArray([[1, 2], [3, 4]]), x=[0, 1], y=0)

    def test_numeral(self):
        test_value = self.state['x']
        value = arith_eval(test_value, self.state)
        self.assertEqual(test_value, value)

    def test_Variable(self):
        test_expr = self.x
        test_value = self.state[test_expr]
        value = arith_eval(test_expr, self.state)
        self.assertEqual(test_value, value)

    def test_UnaryArithExpr(self):
        test_expr = UnaryArithExpr(operators.UNARY_SUBTRACT_OP, self.x)
        test_value = -self.state['x']
        value = arith_eval(test_expr, self.state)
        self.assertEqual(test_value, value)

    def test_BinaryArithExpr(self):
        test_expr = BinaryArithExpr(operators.ADD_OP, self.x, self.y)
        test_value = self.state['x'] + self.state['y']
        value = arith_eval(test_expr, self.state)
        self.assertEqual(test_value, value)

    def test_AccessExpr(self):
        test_expr = AccessExpr(self.a, (self.x, self.y))
        test_value = IntegerInterval([1, 3])
        value = arith_eval(test_expr, self.array_state)
        self.assertEqual(test_value, value)

    def test_UpdateExpr(self):
        test_expr = UpdateExpr(self.a, (self.x, self.y), IntegerInterval(2))
        test_value = IntegerIntervalArray(
            [[IntegerInterval([1, 2]), 2], [IntegerInterval([2, 3]), 4]])
        value = arith_eval(test_expr, self.array_state)
        self.assertEqual(test_value, value)

    def test_SelectExpr(self):
        test_expr = SelectExpr(
            BinaryBoolExpr(operators.LESS_OP, self.x, ErrorSemantics(1.5)),
            IntegerInterval(0), self.y)
        test_value = IntegerInterval(0)
        value = arith_eval(test_expr, self.state)
        self.assertEqual(test_value, value)

        test_expr = SelectExpr(
            BinaryBoolExpr(operators.LESS_OP, self.z, ErrorSemantics(1.5)),
            IntegerInterval(0), self.y)
        test_value = IntegerInterval([0, 3])
        value = arith_eval(test_expr, self.state)
        self.assertEqual(test_value, value)

    def test_FixExpr(self):
        bool_expr = BinaryBoolExpr(operators.LESS_OP, self.x, self.y)
        loop_state = MetaState({
            self.x: BinaryArithExpr(
                operators.ADD_OP, self.x, IntegerInterval(1)),
            self.y: self.y,
        })
        init_state = MetaState({
            self.x: self.x, self.y: self.y,
        })
        test_expr = FixExpr(bool_expr, loop_state, self.x, init_state)
        test_value = IntegerInterval(3)
        value = arith_eval(test_expr, self.state)
        self.assertEqual(test_value, value)

    def test_MetaState(self):
        meta_state = MetaState({
            self.x: BinaryArithExpr(
                operators.ADD_OP, self.x, IntegerInterval(1)),
            self.y: BinaryArithExpr(
                operators.MULTIPLY_OP, self.x, IntegerInterval(2)),
        })
        test_state = BoxState(x=[2, 3], y=[2, 4])
        state = arith_eval(meta_state, self.state)
        self.assertEqual(test_state, state)
