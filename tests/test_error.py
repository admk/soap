import unittest
from gmpy2 import mpfr

from soap.semantics import (
    inf, mpq, mpfr, ulp, FloatInterval, IntegerInterval, ErrorSemantics
)


class TestFoundation(unittest.TestCase):
    """Unittesting for the foundations of roundoff errors."""
    def test_mpfr(self):
        self.assertRaises(ValueError, mpfr, 'foo')
        self.assertEqual(mpfr('1'), mpfr(1))
        self.assertEqual(mpfr('Inf'), float('inf'))

    def test_mpq(self):
        self.assertRaises(ValueError, mpq, 'foo')
        self.assertNotEqual(mpq('1/3'), mpq(mpfr(1) / 3))

    def test_ulp(self):
        one = mpfr(1)
        eps = mpfr(ulp(one, underflow=False))
        mid = (one + (one + eps)) / 2
        self.assertEqual(one, mid)
        self.assertEqual(one, one + eps / 2)
        self.assertLess(one, one + eps)
        self.assertGreater(one, one - eps)


class TestInterval(unittest.TestCase):
    """Unittesting for :class:`soap.semantics.FloatInterval`."""
    def setUp(self):
        self.bottom = FloatInterval(bottom=True)
        self.top = FloatInterval(top=True)
        self.int14 = FloatInterval([1, 4])
        self.int34 = FloatInterval([3, 4])
        self.int29 = FloatInterval([2, 9])

    def test_top_and_bottom(self):
        self.assertEqual(self.top, FloatInterval([-inf, inf]))
        self.assertNotEqual(self.top, FloatInterval([2, inf]))
        self.assertNotEqual(self.top, FloatInterval([-inf, 2]))
        self.assertEqual(self.bottom + self.int14, self.bottom)
        self.assertEqual(self.int14 + self.bottom, self.bottom)
        self.assertEqual(self.top + self.int14, self.top)
        self.assertEqual(self.int14 + self.top, self.top)

    def test_operators(self):
        self.assertEqual(self.int14 + self.int29, FloatInterval([3, 13]))
        self.assertEqual(self.int14 - self.int29, FloatInterval([-8, 2]))
        self.assertEqual(self.int14 * self.int29, FloatInterval([2, 36]))
        self.assertEqual(self.int14 / self.int29, FloatInterval([1 / 9, 2]))
        self.assertEqual(-self.int14, FloatInterval([-4, -1]))

    def test_coercion(self):
        self.assertEqual(1 + self.int29, FloatInterval([3, 10]))
        self.assertEqual(self.int29 + 1, FloatInterval([3, 10]))
        self.assertEqual(1 - self.int29, FloatInterval([-8, -1]))
        self.assertEqual(self.int29 - 1, FloatInterval([1, 8]))
        self.assertEqual(2 * self.int29, FloatInterval([4, 18]))
        self.assertEqual(self.int29 * 2, FloatInterval([4, 18]))
        self.assertEqual(2 / self.int29, FloatInterval([2 / 9, 1]))
        self.assertEqual(self.int29 / 2, FloatInterval([1, 9 / 2]))

    def test_order(self):
        self.assertTrue(self.bottom <= self.int14)
        self.assertFalse(self.int14 <= self.bottom)
        self.assertFalse(self.top <= self.int14)
        self.assertTrue(self.bottom <= self.int14)
        self.assertFalse(self.int14 <= self.int29)
        self.assertTrue(self.int34 <= self.int14)

    def test_join(self):
        self.assertEqual(self.int14 | self.int34, self.int14)
        self.assertEqual(self.int14 | self.int29, FloatInterval([1, 9]))

    def test_meet(self):
        self.assertEqual(self.int14 & self.int34, self.int34)
        self.assertEqual(self.int14 & self.int29, FloatInterval([2, 4]))


class ErrorAssertionTestCase(unittest.TestCase):
    def assertAlmostEqual(self, a, b):
        try:
            self.assertErrorAlmostEqual(a, b)
        except AttributeError:
            self.assertIntervalAlmostEqual(a, b)

    def assertIntervalAlmostEqual(self, a, b):
        super().assertAlmostEqual(a.min, b.min)
        super().assertAlmostEqual(a.max, b.max)

    def assertErrorAlmostEqual(self, a, b):
        self.assertIntervalAlmostEqual(a.v, b.v)
        self.assertIntervalAlmostEqual(a.e, b.e)


class TestErrorSemantics(ErrorAssertionTestCase):
    """Unittesting for :class:`soap.semantics.ErrorSemantics`."""
    def setUp(self):
        self.e1 = ErrorSemantics(['1.2', '2.3'], ['0', '0.1'])
        self.e2 = ErrorSemantics('3.4')
        self.c1 = ErrorSemantics('1')
        self.c2 = ErrorSemantics(2)
        self.top = ErrorSemantics(top=True)
        self.bottom = ErrorSemantics(bottom=True)
        self.e12 = ErrorSemantics(['1.0', '2.0'])
        self.e13 = ErrorSemantics(['1.0', '3.0'])
        self.e24 = ErrorSemantics(['2.0', '4.0'])
        self.e34 = ErrorSemantics(['3.0', '4.0'])

    def test_value_and_error(self):
        l = [
            ErrorSemantics('16'),
            ErrorSemantics(['16', '16']),
            ErrorSemantics(['16', '16'], ['0', '0']),
        ]
        for e in l:
            self.assertEqual(e.v.min, 16)
            self.assertEqual(e.v.max, 16)
            self.assertEqual(e.e.min, 0)
            self.assertEqual(e.e.max, 0)

    def test_top_and_bottom(self):
        self.assertEqual(self.top, ErrorSemantics([-inf, inf]))
        self.assertEqual(self.top, ErrorSemantics([-inf, inf], [-inf, inf]))
        self.assertEqual(self.bottom + self.e1, self.bottom)
        self.assertEqual(self.e1 + self.bottom, self.bottom)
        self.assertEqual(self.top + self.e1, self.top)
        self.assertEqual(self.e1 + self.top, self.top)

    def test_operators(self):
        self.assertEqual(self.e1 + self.e2, self.e2 + self.e1)
        self.assertEqual(self.e1 - self.e2, -(self.e2 - self.e1))
        self.assertEqual(self.e1 * self.e2, self.e2 * self.e1)
        self.assertAlmostEqual(
            (self.e1 + self.e2) / self.e2,
            self.e1 / self.e2 + ErrorSemantics('1'))
        self.assertEqual(-self.e2, ErrorSemantics('-3.4'))

    def test_coercion(self):
        self.assertEqual(self.e1 + 2, self.e1 + self.c2)
        self.assertEqual(2 + self.e1, self.c2 + self.e1)
        self.assertEqual(self.e1 - 2, self.e1 - self.c2)
        self.assertEqual(2 - self.e1, self.c2 - self.e1)
        self.assertEqual(self.e1 * 2, self.e1 * self.c2)
        self.assertEqual(2 * self.e1, self.c2 * self.e1)
        self.assertEqual(self.e1 / 2, self.e1 / self.c2)
        self.assertEqual(2 / self.e1, self.c2 / self.e1)

    def test_order(self):
        self.assertTrue(self.bottom <= self.e1)
        self.assertFalse(self.e1 <= self.bottom)
        self.assertFalse(self.top <= self.e1)
        self.assertTrue(self.bottom <= self.e1)
        self.assertFalse(self.e13 <= self.e24)
        self.assertFalse(self.e24 <= self.e13)
        self.assertTrue(self.e12 <= self.e13)
        self.assertFalse(self.e13 <= self.e12)

    def test_join(self):
        self.assertEqual(self.e12 | self.e24, self.e13 | self.e24)

    def test_meet(self):
        self.assertAlmostEqual(self.e13 & self.e24, ErrorSemantics(['2', '3']))
        self.assertAlmostEqual(self.e12 & self.e24, ErrorSemantics('2'))
        self.assertGreaterEqual(
            self.e12 & self.e34, ErrorSemantics(bottom=True))


class TestCoercion(ErrorAssertionTestCase):
    def setUp(self):
        self.interval = [2, 3]
        self.const = 4
        self.integer = self.const
        self.float = float(self.const)
        self.integer_interval = IntegerInterval(self.interval)
        self.float_interval = FloatInterval(self.interval)
        self.error = ErrorSemantics(self.interval)
        self.interval_tests = [
            (self.integer_interval, self.float_interval, FloatInterval),
            (self.float_interval, self.integer_interval, FloatInterval),
            (self.integer_interval, self.error, ErrorSemantics),
            (self.error, self.integer_interval, ErrorSemantics),
            (self.float_interval, self.error, ErrorSemantics),
            (self.error, self.float_interval, ErrorSemantics),
        ]
        self.const_tests = [
            (self.integer_interval, self.integer, IntegerInterval),
            (self.integer, self.integer_interval, IntegerInterval),
            (self.integer_interval, self.float, FloatInterval),
            (self.float, self.integer_interval, FloatInterval),
            (self.float_interval, self.integer, FloatInterval),
            (self.integer, self.float_interval, FloatInterval),
            (self.float_interval, self.float, FloatInterval),
            (self.float, self.float_interval, FloatInterval),
            (self.error, self.integer, ErrorSemantics),
            (self.integer, self.error, ErrorSemantics),
            (self.error, self.float, ErrorSemantics),
            (self.float, self.error, ErrorSemantics),
        ]

    def trials(self, funcs, tests):
        for i, j, t in tests:
            for f in funcs:
                u = f(i, j)
                v = f(t(i), t(j))
                if isinstance(u, bool):
                    continue
                self.assertEqual(type(u), t)
                self.assertAlmostEqual(u, v)

    def test_operators(self):
        self.trials([
            lambda x, y: x + y,
            lambda x, y: x - y,
            lambda x, y: x * y,
        ], self.interval_tests + self.const_tests)

    def test_lattice(self):
        self.trials([
            lambda x, y: x | y,
            lambda x, y: x & y,
            lambda x, y: x <= y,
            lambda x, y: x < y,
            lambda x, y: x == y,
            lambda x, y: x >= y,
            lambda x, y: x > y,
            lambda x, y: x != y,
        ], self.interval_tests)
