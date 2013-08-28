import unittest
import gmpy2

from soap.expr import Expr
from soap.expr import ADD_OP, UNARY_SUBTRACT_OP


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

    def test_binary_expr_init(self):
        e = Expr('a + b')
        self.assertEqual(e.op, ADD_OP)
        self.assertEqual(e.a1, 'a')
        self.assertEqual(e.a2, 'b')

    def test_unary_expr_init(self):
        e = Expr('-a')
        self.assertEqual(e.op, UNARY_SUBTRACT_OP)
        self.assertEqual(e.a1, 'a')
        self.assertIsNone(e.a2)

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

    def test_str(self):
        self.assertEqual(Expr(str(self.e)), self.e)
