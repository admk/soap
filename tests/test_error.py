import unittest

from soap.semantics import Interval


class TestInterval(unittest.TestCase):
    def setUp(self):
        self.bottom = Interval(bottom=True)
        self.top = Interval(top=True)
        self.int14 = Interval([1, 4])
        self.int34 = Interval([3, 4])
        self.int29 = Interval([2, 9])

    def test_top_and_bottom(self):
        self.assertEqual(self.bottom + self.int14, self.bottom)
        self.assertEqual(self.int14 + self.bottom, self.bottom)
        self.assertEqual(self.top + self.int14, self.top)
        self.assertEqual(self.int14 + self.top, self.top)

    def test_operators(self):
        self.assertEqual(self.int14 + self.int29, Interval([3, 13]))
        self.assertEqual(self.int14 - self.int29, Interval([-8, 2]))
        self.assertEqual(self.int14 * self.int29, Interval([2, 36]))
        self.assertEqual(-self.int14, Interval([-4, -1]))

    def test_multi_type_operators(self):
        self.assertEqual(1 + self.int29, Interval([3, 10]))
        self.assertEqual(self.int29 + 1, Interval([3, 10]))
        self.assertEqual(1 - self.int29, Interval([-8, -1]))
        self.assertEqual(self.int29 - 1, Interval([1, 8]))
        self.assertEqual(2 * self.int29, Interval([4, 18]))
        self.assertEqual(self.int29 * 2, Interval([4, 18]))

    def test_order(self):
        self.assertFalse(self.int14 <= self.int29)
        self.assertTrue(self.int34 <= self.int14)

    def test_join(self):
        self.assertEqual(self.int14 | self.int34, self.int14)
        self.assertEqual(self.int14 | self.int29, Interval([1, 9]))

    def test_meet(self):
        self.assertEqual(self.int14 & self.int34, self.int34)
        self.assertEqual(self.int14 & self.int29, Interval([2, 4]))
