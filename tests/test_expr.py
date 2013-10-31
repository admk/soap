import unittest
import os
import gmpy2

from soap.expression import (
    Var, Expr, BoolExpr,
    ADD_OP, UNARY_SUBTRACT_OP, LESS_OP, EQUAL_OP, UNARY_NEGATION_OP
)


skip = 'NOSE_SKIP' in os.environ


class TestExpr(unittest.TestCase):
    """Unittesting for :class:`soap.expression.Expr`."""
    def setUp(self):
        self.e = Expr('(a + a + b) * (a + b + b) * (b + b + c)')
        self.f = Expr('(b + b + c) * (a + a + b) * (a + b + b)')
        self.v = {
            'a': ['1.0', '2.0'],
            'b': ['10', '20.0'],
            'c': ['100.0', '200'],
        }
        self.p = gmpy2.ieee(32).precision - 1

    def test_binary_expr_parse_init(self):
        e = Expr('a + b')
        self.assertEqual(e.op, ADD_OP)
        self.assertEqual(e.a1, Var('a'))
        self.assertEqual(e.a2, Var('b'))

    def test_binary_arith_expr_multi_init(self):
        e = Expr(ADD_OP, Var('a'), Var('b'))
        f = Expr(ADD_OP, [Var('a'), Var('b')])
        g = Expr(op=ADD_OP, al=[Var('a'), Var('b')])
        h = Expr(op=ADD_OP, a1=Var('a'), a2=Var('b'))
        l1 = [e, f, g, h]
        l2 = [f, g, h, e]
        for e1, e2 in zip(l1, l2):
            self.assertEqual(e1, e2)

    def test_unary_arith_expr_parse_init(self):
        l = [
            Expr('-a'),
            Expr(UNARY_SUBTRACT_OP, Var('a')),
            Expr(op=UNARY_SUBTRACT_OP, a=Var('a')),
            Expr(op=UNARY_SUBTRACT_OP, al=[Var('a')]),
        ]
        for e in l:
            self.assertEqual(e.op, UNARY_SUBTRACT_OP)
            self.assertEqual(e.a1, Var('a'))
            self.assertIsNone(e.a2)

    def test_binary_bool_expr_init(self):
        self.assertEqual(
            BoolExpr('a < b'), BoolExpr(LESS_OP, Var('a'), Var('b')))
        self.assertEqual(
            BoolExpr('a == b'), BoolExpr(EQUAL_OP, Var('a'), Var('b')))

    def test_unary_bool_expr_init(self):
        l = [
            BoolExpr('~a'),
            BoolExpr(UNARY_NEGATION_OP, Var('a')),
            BoolExpr(op=UNARY_NEGATION_OP, a=Var('a')),
            BoolExpr(op=UNARY_NEGATION_OP, al=[Var('a')]),
        ]
        for e in l:
            self.assertEqual(e.op, UNARY_NEGATION_OP)
            self.assertEqual(e.a1, Var('a'))
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
        env = {'a': 1, 'b': 10, 'c': 100}
        env = {Var(k): v for k, v in env.items()}
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
            e = Expr('a + b')
            self.assertAlmostEqual(
                e.area(self.v, self.p).area, e.real_area(self.v, self.p))
        except ImportError:
            raise SkipTest

    def test_equal(self):
        self.assertEqual(Expr('a + b'), Expr('b + a'))
        self.assertNotEqual(Expr('a - b'), Expr('b - a'))

    def test_str(self):
        self.assertEqual(Expr(str(self.e)), self.e)
