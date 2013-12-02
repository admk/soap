import unittest

from soap.expression import expr
from soap.transformer import pattern
from soap.transformer.arithmetic import (
    associativity_addition, associativity_multiplication,
    distribute_for_distributivity, collect_for_distributivity,
    multiplicative_identity_reduction, additive_identity_reduction,
    zero_reduction, constant_2_ary_reduction
)
from soap.transformer.utils import parsings, reduce


class TestArithmeticEquivalence(unittest.TestCase):
    """
    Unit testing for :mod:`soap.transformer.arithmetic`.
    """
    def test_associativity(self):
        e = expr('(a + b) + c')
        f = pattern.transform(associativity_addition, e)
        self.assertIn(expr('a + (b + c)'), f)
        self.assertIn(expr('b + (a + c)'), f)
        e = expr('(a * b) * c')
        f = pattern.transform(associativity_multiplication, e)
        self.assertIn(expr('a * (b * c)'), f)
        self.assertIn(expr('b * (a * c)'), f)

    def test_distribute_for_distributivity(self):
        e = expr('(a + b) * c')
        f = pattern.transform(distribute_for_distributivity, e)
        self.assertIn(expr('a * c + b * c'), f)

    def test_collect_for_distributivity(self):
        e = expr('a * c + b * c')
        f = pattern.transform(collect_for_distributivity, e)
        self.assertIn(expr('(a + b) * c'), f)

    def test_multiplicative_identity_reduction(self):
        e = expr('a * 1')
        f = pattern.transform(multiplicative_identity_reduction, e)
        self.assertIn(expr('a'), f)

    def test_additive_identity_reduction(self):
        e = expr('a + 0')
        f = pattern.transform(additive_identity_reduction, e)
        self.assertIn(expr('a'), f)

    def test_zero_reduction(self):
        e = expr('a * 0')
        f = pattern.transform(zero_reduction, e)
        self.assertIn(expr('0'), f)

    def test_constant_reduction(self):
        e = expr('1 + 2')
        f = pattern.transform(constant_2_ary_reduction, e)
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
