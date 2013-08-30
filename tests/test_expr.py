import unittest
import gmpy2

from soap.expr import Expr, BoolExpr
from soap.expr import (
    ADD_OP, UNARY_SUBTRACT_OP, LESS_OP, EQUAL_OP, UNARY_NEGATION_OP
)


class TestExpr(unittest.TestCase):
    """Unittesting for :class:`soap.expr.Expr`."""
    def setUp(self):
        self.e = Expr('(a + a + b) * (a + b + b) * (b + b + c)')
        self.f = Expr('(b + b + c) * (a + a + b) * (a + b + b)')
        self.v = {
            'a': ['1', '2'],
            'b': ['10', '20'],
            'c': ['100', '200'],
        }
        self.p = gmpy2.ieee(32).precision - 1

    def test_binary_expr_parse_init(self):
        e = Expr('a + b')
        self.assertEqual(e.op, ADD_OP)
        self.assertEqual(e.a1, 'a')
        self.assertEqual(e.a2, 'b')

    def test_binary_arith_expr_multi_init(self):
        e = Expr(ADD_OP, 'a', 'b')
        f = Expr(ADD_OP, ['a', 'b'])
        g = Expr(op=ADD_OP, al=['a', 'b'])
        h = Expr(op=ADD_OP, a1='a', a2='b')
        l1 = [e, f, g, h]
        l2 = [f, g, h, e]
        for e1, e2 in zip(l1, l2):
            self.assertEqual(e1, e2)

    def test_unary_arith_expr_parse_init(self):
        l = [
            Expr('-a'),
            Expr(UNARY_SUBTRACT_OP, 'a'),
            Expr(op=UNARY_SUBTRACT_OP, a='a'),
            Expr(op=UNARY_SUBTRACT_OP, al=['a']),
        ]
        for e in l:
            self.assertEqual(e.op, UNARY_SUBTRACT_OP)
            self.assertEqual(e.a1, 'a')
            self.assertIsNone(e.a2)

    def test_binary_bool_expr_init(self):
        self.assertEqual(BoolExpr('a < b'), BoolExpr(LESS_OP, 'a', 'b'))
        self.assertEqual(BoolExpr('a == b'), BoolExpr(EQUAL_OP, 'a', 'b'))

    def test_unary_bool_expr_init(self):
        l = [
            BoolExpr('~a'),
            BoolExpr(UNARY_NEGATION_OP, 'a'),
            BoolExpr(op=UNARY_NEGATION_OP, a='a'),
            BoolExpr(op=UNARY_NEGATION_OP, al=['a']),
        ]
        for e in l:
            self.assertEqual(e.op, UNARY_NEGATION_OP)
            self.assertEqual(e.a1, 'a')
            self.assertIsNone(e.a2)
        e = BoolExpr('a < b')
        self.assertEqual(~e, BoolExpr(UNARY_NEGATION_OP, e))

    def test_binary_arith_expr_operator(self):
        e = Expr('a + b')
        f = Expr('b + c')
        self.assertEqual(e * f, Expr('(a + b) * (b + c)'))

    def test_unary_arith_expr_operator(self):
        e = Expr('a + b')
        self.assertEqual(-e, Expr('-(a + b)'))

    def test_crop_and_stitch(self):
        cropped_expr, cropped_env = self.e.crop(1)
        self.assertNotEqual(cropped_expr, self.e)
        self.assertEqual(self.e, self.e.stitch(cropped_env))

    def test_eval(self):
        v = {'a': 1, 'b': 10, 'c': 100}
        self.assertEqual(self.e.eval(v), self.f.eval(v))

    def test_error(self):
        e, f = self.e.error(self.v, self.p), self.f.error(self.v, self.p)
        self.assertAlmostEqual(e.v.min, f.v.min)
        self.assertAlmostEqual(e.v.max, f.v.max)

    def test_area(self):
        self.assertAlmostEqual(
            self.e.area(self.v, self.p).area, self.f.area(self.v, self.p).area)

    def test_real_area(self):
        try:
            e = Expr('a + b')
            self.assertAlmostEqual(
                e.area(self.v, self.p).area, e.real_area(self.v, self.p))
        except ImportError:
            from nose.plugins.skip import SkipTest
            raise SkipTest

    def test_equal(self):
        self.assertEqual(Expr('a + b'), Expr('b + a'))
        self.assertNotEqual(Expr('a - b'), Expr('b - a'))

    def test_str(self):
        self.assertEqual(Expr(str(self.e)), self.e)
