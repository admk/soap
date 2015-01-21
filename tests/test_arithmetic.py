import unittest

from soap.expression.fixpoint import FixExpr
from soap.expression.linalg import AccessExpr, UpdateExpr
from soap.parser.program import parse
from soap.semantics.error import IntegerInterval
from soap.semantics.functions.arithmetic import arith_eval
from soap.semantics.linalg import IntegerIntervalArray
from soap.semantics.state.box import BoxState
from soap.semantics.state.meta import MetaState


class TestArithmeticEvaluator(unittest.TestCase):
    def setUp(self):
        self.state = BoxState(x=[1, 2], y=3)
        self.array_state = BoxState(
            x=IntegerIntervalArray([[1, 2], [3, 4]]), i=[0, 1], j=0)

    def test_numeral(self):
        test_value = self.state['x']
        value = arith_eval(test_value, self.state)
        self.assertEqual(test_value, value)

    def test_Variable(self):
        test_expr = parse('x')
        test_value = self.state[test_expr]
        value = arith_eval(test_expr, self.state)
        self.assertEqual(test_value, value)

    def test_UnaryArithExpr(self):
        test_expr = parse('-x')
        test_value = -self.state['x']
        value = arith_eval(test_expr, self.state)
        self.assertEqual(test_value, value)

    def test_BinaryArithExpr(self):
        test_expr = parse('x + y')
        test_value = self.state['x'] + self.state['y']
        value = arith_eval(test_expr, self.state)
        self.assertEqual(test_value, value)

    def test_AccessExpr(self):
        test_expr = AccessExpr(parse('x'), (parse('i'), parse('j')))
        test_value = IntegerInterval([1, 3])
        value = arith_eval(test_expr, self.array_state)
        self.assertEqual(test_value, value)

    def test_UpdateExpr(self):
        test_expr = UpdateExpr(
            parse('x'), (parse('i'), parse('j')), parse('2'))
        test_value = IntegerIntervalArray(
            [[IntegerInterval([1, 2]), 2], [IntegerInterval([2, 3]), 4]])
        value = arith_eval(test_expr, self.array_state)
        self.assertEqual(test_value, value)

    def test_SelectExpr(self):
        test_expr = parse('(x < 1.5) ? 0 : y')
        test_value = IntegerInterval([0, 3])
        value = arith_eval(test_expr, self.state)
        self.assertEqual(test_value, value)

    def test_FixExpr(self):
        bool_expr = parse('(x < y)')
        loop_state = MetaState(x='x + 1', y='y')
        init_state = MetaState(x='x', y='y')
        test_expr = FixExpr(bool_expr, loop_state, parse('x'), init_state)
        test_value = IntegerInterval(3)
        value = arith_eval(test_expr, self.state)
        self.assertEqual(test_value, value)

    def test_MetaState(self):
        meta_state = MetaState(x='x + 1', y='x * 2')
        test_state = BoxState(x=[2, 3], y=[2, 4])
        state = arith_eval(meta_state, self.state)
        self.assertEqual(test_state, state)
