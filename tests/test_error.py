import unittest
from gmpy2 import mpfr

from soap.semantics import (
    Interval, FloatInterval, IntegerInterval, ErrorSemantics
)


inf = mpfr('Inf')


class TestInterval(unittest.TestCase):
    """Unittesting for :class:`soap.semantics.Interval`."""
    def setUp(self):
        self.bottom = Interval(bottom=True)
        self.top = Interval(top=True)
        self.int14 = Interval([1, 4])
        self.int34 = Interval([3, 4])
        self.int29 = Interval([2, 9])

    def test_top_and_bottom(self):
        self.assertEqual(self.top, Interval([-inf, inf]))
        self.assertNotEqual(self.top, Interval([2, inf]))
        self.assertNotEqual(self.top, Interval([-inf, 2]))
        self.assertEqual(self.bottom + self.int14, self.bottom)
        self.assertEqual(self.int14 + self.bottom, self.bottom)
        self.assertEqual(self.top + self.int14, self.top)
        self.assertEqual(self.int14 + self.top, self.top)

    def test_operators(self):
        self.assertEqual(self.int14 + self.int29, Interval([3, 13]))
        self.assertEqual(self.int14 - self.int29, Interval([-8, 2]))
        self.assertEqual(self.int14 * self.int29, Interval([2, 36]))
        self.assertEqual(self.int14 / self.int29, Interval([1 / 9, 2]))
        self.assertEqual(-self.int14, Interval([-4, -1]))

    def test_coercion(self):
        self.assertEqual(1 + self.int29, Interval([3, 10]))
        self.assertEqual(self.int29 + 1, Interval([3, 10]))
        self.assertEqual(1 - self.int29, Interval([-8, -1]))
        self.assertEqual(self.int29 - 1, Interval([1, 8]))
        self.assertEqual(2 * self.int29, Interval([4, 18]))
        self.assertEqual(self.int29 * 2, Interval([4, 18]))
        self.assertEqual(2 / self.int29, Interval([2 / 9, 1]))
        self.assertEqual(self.int29 / 2, Interval([1, 9 / 2]))

    def test_order(self):
        self.assertTrue(self.bottom <= self.int14)
        self.assertFalse(self.int14 <= self.bottom)
        self.assertFalse(self.top <= self.int14)
        self.assertTrue(self.bottom <= self.int14)
        self.assertFalse(self.int14 <= self.int29)
        self.assertTrue(self.int34 <= self.int14)

    def test_join(self):
        self.assertEqual(self.int14 | self.int34, self.int14)
        self.assertEqual(self.int14 | self.int29, Interval([1, 9]))

    def test_meet(self):
        self.assertEqual(self.int14 & self.int34, self.int34)
        self.assertEqual(self.int14 & self.int29, Interval([2, 4]))


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
        self.integer_interval = IntegerInterval(self.interval)
        self.float_interval = FloatInterval(self.interval)
        self.error = ErrorSemantics(self.interval)

    def trials(self, funcs):
        tests = [
            (self.integer_interval, self.float_interval, FloatInterval),
            (self.float_interval, self.integer_interval, FloatInterval),
            (self.integer_interval, self.error, ErrorSemantics),
            (self.error, self.integer_interval, ErrorSemantics),
            (self.float_interval, self.error, ErrorSemantics),
            (self.error, self.float_interval, ErrorSemantics),
        ]
        for i, j, t in tests:
            for f in funcs:
                u = f(i, j)
                v = t(self.interval)
                v = f(v, v)
                if not isinstance(u, bool):
                    self.assertEqual(type(u), t)
                    self.assertAlmostEqual(u, v)

    def test_operators(self):
        self.trials([
            lambda x, y: x + y,
            lambda x, y: x - y,
            lambda x, y: x * y,
        ])

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
        ])
