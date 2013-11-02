import unittest
import os
import gmpy2

from soap.expression import (
    expr, Variable, UnaryArithExpr, BinaryArithExpr, UnaryBoolExpr,
    BinaryBoolExpr, ADD_OP, UNARY_SUBTRACT_OP, LESS_OP, UNARY_NEGATION_OP
)


skip = 'NOSE_SKIP' in os.environ


class TestExpr(unittest.TestCase):
    """Unittesting for :mod:`soap.expression`."""
    def setUp(self):
        self.e = expr('(a + a + b) * (a + b + b) * (b + b + c)')
        self.f = expr('(b + b + c) * (a + a + b) * (a + b + b)')
        self.v = {
            'a': ['1.0', '2.0'],
            'b': ['10', '20.0'],
            'c': ['100.0', '200'],
        }
        self.p = gmpy2.ieee(32).precision - 1

    def test_unary_arith_expr_parse_init(self):
        e = expr('-a')
        self.assertIsInstance(e, UnaryArithExpr)
        self.assertEqual(e.op, UNARY_SUBTRACT_OP)
        self.assertEqual(e.a, Variable('a'))

    def test_binary_arith_expr_parse_init(self):
        e = expr('a + b')
        self.assertIsInstance(e, BinaryArithExpr)
        self.assertEqual(e.op, ADD_OP)
        self.assertEqual(e.a1, Variable('a'))
        self.assertEqual(e.a2, Variable('b'))

    def test_unary_bool_expr_init(self):
        e = expr('~a')
        self.assertIsInstance(e, UnaryBoolExpr)
        self.assertEqual(e.op, UNARY_NEGATION_OP)
        self.assertEqual(e.a, Variable('a'))

    def test_binary_bool_expr_init(self):
        e = expr('a < b')
        self.assertIsInstance(e, BinaryBoolExpr)
        self.assertEqual(e.op, LESS_OP)
        self.assertEqual(e.a1, Variable('a'))
        self.assertEqual(e.a2, Variable('b'))

    def test_binary_arith_expr_operator(self):
        e = expr('a + b')
        f = expr('b + c')
        self.assertEqual(e * f, expr('(a + b) * (b + c)'))

    def test_unary_arith_expr_operator(self):
        e = expr('a + b')
        self.assertEqual(-e, expr('-(a + b)'))

    def test_crop_and_stitch(self):
        cropped_expr, cropped_env = self.e.crop(1)
        self.assertNotEqual(cropped_expr, self.e)
        self.assertEqual(self.e, self.e.stitch(cropped_env))

    def test_eval(self):
        env = {'a': 1, 'b': 10, 'c': 100}
        env = {Variable(k): v for k, v in env.items()}
        self.assertEqual(self.e.eval(env), self.f.eval(env))

    def test_error(self):
        e, f = self.e.error(self.v, self.p), self.f.error(self.v, self.p)
        self.assertAlmostEqual(e.v.min, f.v.min)
        self.assertAlmostEqual(e.v.max, f.v.max)

    def test_area(self):
        self.assertAlmostEqual(
            self.e.area(self.v, self.p).area, self.f.area(self.v, self.p).area)

    def test_real_area(self):
        from nose.plugins.skip import SkipTest
        if skip:
            raise SkipTest
        try:
            e = expr('a + b')
            self.assertAlmostEqual(
                e.area(self.v, self.p).area, e.real_area(self.v, self.p))
        except ImportError:
            raise SkipTest

    def test_equal(self):
        self.assertEqual(expr('a + b'), expr('b + a'))
        self.assertNotEqual(expr('a - b'), expr('b - a'))

    def test_str(self):
        self.assertEqual(expr(str(self.e)), self.e)
