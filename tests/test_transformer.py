import unittest

from soap.expression import expr
from soap.expression.base import Expression
from soap.transformer import pattern
from soap.transformer import arithmetic
from soap.transformer.utils import parsings, reduce

Expression.__repr__ = lambda self: self.__str__()


class TestArithmeticEquivalence(unittest.TestCase):
    """
    Unit testing for :mod:`soap.transformer.arithmetic`.
    """
    def test_associativity(self):
        for e in ['(a + b) + c', '(b + a) + c', 'c + (a + b)', 'c + (b + a)']:
            f = pattern.transform(arithmetic.associativity_addition, expr(e))
            self.assertIn(expr('a + (b + c)'), f)
            self.assertIn(expr('b + (a + c)'), f)
        for e in ['(a * b) * c', '(b * a) * c', 'c * (a * b)', 'c * (b * a)']:
            f = pattern.transform(
                arithmetic.associativity_multiplication, expr(e))
            self.assertIn(expr('a * (b * c)'), f)
            self.assertIn(expr('b * (a * c)'), f)

    def test_distributivity_distribute(self):
        for e in ['(a + b) * c', '(b + a) * c', 'c * (a + b)', 'c * (b + a)']:
            f = pattern.transform(
                arithmetic.distributivity_distribute_multiplication, expr(e))
            self.assertIn(expr('a * c + b * c'), f)

    def test_distributivity_collect(self):
        e = expr('c * a + b * c')
        f = pattern.transform(
            arithmetic.distributivity_collect_multiplication, e)
        self.assertIn(expr('(a + b) * c'), f)

    def test_identity_reduction(self):
        e = expr('0 + a')
        f = pattern.transform(arithmetic.identity_reduction_addition, e)
        self.assertIn(expr('a'), f)
        e = expr('1 * a')
        f = pattern.transform(arithmetic.identity_reduction_multiplication, e)
        self.assertIn(expr('a'), f)
        e = expr('a / 1')
        f = pattern.transform(arithmetic.identity_reduction_division, e)
        self.assertIn(expr('a'), f)

    def test_zero_reduction(self):
        e = expr('a * 0')
        f = pattern.transform(arithmetic.zero_reduction_multiplication, e)
        self.assertIn(expr('0'), f)
        e = expr('0 / a')
        f = pattern.transform(arithmetic.zero_reduction_division, e)
        self.assertIn(expr('0'), f)

    def test_constant_reduction(self):
        e = expr('1 + 2')
        f = pattern.transform(arithmetic.constant_reduction, e)
        self.assertIn(expr('3'), f)


class TestArithTreeTransformer(unittest.TestCase):
    """
    Unit testing for :class:`soap.transformer.arithmetic.ArithTreeTransformer`.
    """
    def test_parsings(self):
        e = expr('a + b + c + d')
        f = parsings(e)
        g = {
            expr('((a + b) + c) + d'),
            expr('(a + (b + c)) + d'),
            expr('(a + (b + d)) + c'),
            expr('(a + b) + (c + d)'),
            expr('(a + c) + (b + d)'),
            expr('(b + (a + c)) + d'),
            expr('(b + (a + d)) + c'),
            expr('(b + c) + (a + d)'),
            expr('a + ((b + c) + d)'),
            expr('a + (b + (c + d))'),
            expr('a + (c + (b + d))'),
            expr('b + ((a + c) + d)'),
            expr('b + ((a + d) + c)'),
            expr('b + (a + (c + d))'),
            expr('c + ((a + b) + d)'),
        }
        self.assertEqual(f, g)

    def test_reduction(self):
        e = {
            expr('a + 1 * b'),
            expr('a * 1 + b'),
            expr('(a + 0) + b'),
        }
        f = reduce(e)
        g = {
            expr('a + b')
        }
        self.assertEqual(f, g)
