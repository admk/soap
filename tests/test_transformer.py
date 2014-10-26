import unittest

from soap.parser import parse
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
            f = pattern.transform(arithmetic.associativity_addition, parse(e))
            self.assertIn(parse('a + (b + c)'), f)
            self.assertIn(parse('b + (a + c)'), f)
        for e in ['(a * b) * c', '(b * a) * c', 'c * (a * b)', 'c * (b * a)']:
            f = pattern.transform(
                arithmetic.associativity_multiplication, parse(e))
            self.assertIn(parse('a * (b * c)'), f)
            self.assertIn(parse('b * (a * c)'), f)

    def test_distributivity_distribute(self):
        for e in ['(a + b) * c', '(b + a) * c', 'c * (a + b)', 'c * (b + a)']:
            f = pattern.transform(
                arithmetic.distributivity_distribute_multiplication, parse(e))
            self.assertIn(parse('a * c + b * c'), f)
        e = parse('-(a + b)')
        f = pattern.transform(
            arithmetic.distributivity_distribute_unary_subtraction_addition, e)
        self.assertIn(parse('-a - b'), f)

    def test_distributivity_collect(self):
        e = parse('c * a + b * c')
        f = pattern.transform(
            arithmetic.distributivity_collect_multiplication, e)
        self.assertIn(parse('(a + b) * c'), f)

    def test_negation(self):
        e = parse('a - b')
        f = pattern.transform(arithmetic.negation, e)
        self.assertIn(parse('a + -b'), f)

    def test_identity_reduction(self):
        e = parse('0 + a')
        f = pattern.transform(arithmetic.identity_reduction_addition, e)
        self.assertIn(parse('a'), f)
        e = parse('1 * a')
        f = pattern.transform(arithmetic.identity_reduction_multiplication, e)
        self.assertIn(parse('a'), f)
        e = parse('a / 1')
        f = pattern.transform(arithmetic.identity_reduction_division, e)
        self.assertIn(parse('a'), f)

    def test_double_negation_reduction(self):
        e = parse('--a')
        f = pattern.transform(arithmetic.double_negation_reduction, e)
        self.assertIn(parse('a'), f)

    def test_zero_reduction(self):
        e = parse('a * 0')
        f = pattern.transform(arithmetic.zero_reduction_multiplication, e)
        self.assertIn(parse('0'), f)
        e = parse('0 / a')
        f = pattern.transform(arithmetic.zero_reduction_division, e)
        self.assertIn(parse('0'), f)

    def test_constant_reduction(self):
        e = parse('1 + 2')
        f = pattern.transform(arithmetic.constant_reduction, e)
        self.assertIn(parse('3'), f)


class TestArithTreeTransformer(unittest.TestCase):
    """
    Unit testing for :class:`soap.transformer.arithmetic.ArithTreeTransformer`.
    """
    def test_parsings(self):
        e = parse('a + b + c + d')
        f = parsings(e)
        g = {
            parse('((a + b) + c) + d'),
            parse('(a + (b + c)) + d'),
            parse('(a + (b + d)) + c'),
            parse('(a + b) + (c + d)'),
            parse('(a + c) + (b + d)'),
            parse('(b + (a + c)) + d'),
            parse('(b + (a + d)) + c'),
            parse('(b + c) + (a + d)'),
            parse('a + ((b + c) + d)'),
            parse('a + (b + (c + d))'),
            parse('a + (c + (b + d))'),
            parse('b + ((a + c) + d)'),
            parse('b + ((a + d) + c)'),
            parse('b + (a + (c + d))'),
            parse('c + ((a + b) + d)'),
        }
        self.assertEqual(f, g)

    def test_reduction(self):
        e = {
            parse('a + 1 * b'),
            parse('a * 1 + b'),
            parse('(a + 0) + b'),
        }
        f = reduce(e)
        g = {
            parse('a + b')
        }
        self.assertEqual(f, g)
