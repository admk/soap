import unittest
import itertools

from soap.semantics.lattice import Lattice, flat, power


class TestLattice(unittest.TestCase):
    """Unittesting for :class:`soap.semantics.lattice.Lattice`."""
    def test_top_and_bottom(self):
        class AltLattice(Lattice):
            pass
        self.assertEqual(Lattice(bottom=True), Lattice(bottom=True))
        self.assertEqual(Lattice(top=True), Lattice(top=True))
        self.assertNotEqual(Lattice(bottom=True), Lattice(top=True))


class TestFlatLattice(unittest.TestCase):
    """Unittesting for :class:`soap.semantics.lattice.FlatLattice`."""
    def setUp(self):
        self.Lat = flat(int, 'IntLattice')
        self.b, self.t = self.Lat(bottom=True), self.Lat(top=True)
        self.FLat = flat([1, 2, 3], 'FiniteLattice')
        self.fb, self.ft = self.FLat(bottom=True), self.FLat(top=True)

    def test_top_and_bottom(self):
        self.assertEqual(self.Lat(bottom=True), self.Lat(bottom=True))
        self.assertEqual(self.Lat(top=True), self.Lat(top=True))
        self.assertEqual(self.FLat(bottom=True), self.FLat(bottom=True))
        self.assertEqual(self.FLat(top=True), self.FLat(top=True))

    def test_flat_lattice_join(self):
        self.assertEqual(self.b | self.b, self.b)
        self.assertEqual(self.b | self.Lat(1), self.Lat(1))
        self.assertEqual(self.Lat(1) | self.b, self.Lat(1))
        self.assertEqual(self.Lat(1) | self.Lat(2), self.t)
        self.assertEqual(self.Lat(1) | self.t, self.t)
        self.assertEqual(self.t | self.Lat(1), self.t)
        self.assertEqual(self.t | self.t, self.t)

    def test_flat_lattice_meet(self):
        self.assertEqual(self.b & self.b, self.b)
        self.assertEqual(self.b & self.Lat(1), self.b)
        self.assertEqual(self.Lat(1) & self.b, self.b)
        self.assertEqual(self.Lat(1) & self.Lat(2), self.b)
        self.assertEqual(self.Lat(1) & self.t, self.Lat(1))
        self.assertEqual(self.t & self.Lat(1), self.Lat(1))
        self.assertEqual(self.t & self.t, self.t)

    def test_flat_lattice_from_set(self):
        self.assertEqual(self.FLat(1), self.FLat(1))
        self.assertNotEqual(self.FLat(1), self.FLat(2))
        self.assertNotEqual(self.FLat(1), self.fb)
        self.assertNotEqual(self.FLat(1), self.ft)
        self.assertEqual(self.fb | self.FLat(1), self.FLat(1))
        self.assertEqual(self.ft | self.FLat(1), self.ft)
        self.assertEqual(self.FLat(1) | self.fb, self.FLat(1))
        self.assertEqual(self.FLat(1) | self.ft, self.ft)
        self.assertEqual(self.FLat(1) | self.FLat(2), self.ft)
        self.assertEqual(self.fb & self.FLat(1), self.fb)
        self.assertEqual(self.ft & self.FLat(1), self.FLat(1))
        self.assertEqual(self.FLat(1) & self.fb, self.fb)
        self.assertEqual(self.FLat(1) & self.ft, self.FLat(1))
        self.assertEqual(self.FLat(1) & self.FLat(2), self.fb)
        with self.assertRaises(ValueError):
            self.FLat(4)


class TestPowerLattice(unittest.TestCase):
    """Unittesting for :class:`soap.semantics.PowerLattice`."""
    def setUp(self):
        self.ILat = power(int)
        self.ib, self.it = self.ILat(bottom=True), self.ILat(top=True)
        self.FLat = power([1, 2, 3])
        self.fb, self.ft = self.FLat(bottom=True), self.FLat(top=True)

    def test_infinite_power_lattice(self):
        self.assertEqual(self.ib | self.ib, self.ib)
        self.assertEqual(self.ib | self.ILat([1]), self.ILat([1]))
        self.assertEqual(self.ILat([1]) | self.ib, self.ILat([1]))
        self.assertEqual(self.ILat([1]) | self.ILat([2]), self.ILat([1, 2]))
        self.assertEqual(self.ILat([1]) | self.it, self.it)
        self.assertEqual(self.it | self.ILat([1]), self.it)
        self.assertEqual(self.it | self.it, self.it)


class TestComponentWiseLattice(unittest.TestCase):
    """Unittesting for :class:`soap.semantics.LatticeMeta`
    ComponentWiseLattice."""
    def setUp(self):
        self.alphabets = ['a']
        self.numerals = [1]
        self.Alphabet = flat(self.alphabets, name='Alphabet')
        self.Numeral = flat(self.numerals, name='Numeral')
        self.AlphaNumeral = self.Alphabet * self.Numeral
        self.alphabets += ['top', 'bottom']
        self.numerals += ['top', 'bottom']

    def test_top_and_bottom(self):
        self.assertEqual(
            self.AlphaNumeral('top', 'top'), self.AlphaNumeral(top=True))
        self.assertEqual(
            self.AlphaNumeral('bottom', 'bottom'),
            self.AlphaNumeral(bottom=True))

    def test_component_wise_lattice_order(self):
        t, b, a = 'top', 'bottom', 'a'
        rel_tests = {
            (t, t): [(t, 1), (t, b), (a, t), (a, 1), (a, b),
                     (b, t), (b, 1), (b, b)],
            (t, 1): [(t, b), (a, 1), (a, b), (b, 1), (b, b)],
            (t, b): [(a, b), (b, b)],
            (a, t): [(a, 1), (a, b), (b, t), (b, 1), (b, b)],
            (a, 1): [(a, b), (b, 1), (b, b)],
            (a, b): [(b, b)],
            (b, t): [(b, 1), (b, b)],
            (b, 1): [(b, b)],
            (b, b): [],
        }
        for a1, n1 in itertools.product(self.alphabets, self.numerals):
            l1 = self.AlphaNumeral(a1, n1)
            for a2, n2 in itertools.product(self.alphabets, self.numerals):
                l2 = self.AlphaNumeral(a2, n2)
                test = (a1, n1) in rel_tests[a2, n2]
                same = (a1, n1) == (a2, n2)
                self.assertEqual(l1 <= l2, test or same)
        self.assertEqual(
            self.AlphaNumeral(top=True), self.AlphaNumeral('top', 'top'))
        self.assertEqual(
            self.AlphaNumeral(self.Alphabet('a'), self.Numeral(1)),
            self.AlphaNumeral('a', 1))

    def test_component_wise_lattice_join_and_meet(self):
        t, b, a = 'top', 'bottom', 'a'
        join_tests = {
            ((t, t), (t, t)): (t, t), ((t, t), (t, 1)): (t, t),
            ((t, t), (t, b)): (t, t), ((t, t), (a, t)): (t, t),
            ((t, t), (a, 1)): (t, t), ((t, t), (a, b)): (t, t),
            ((t, t), (b, t)): (t, t), ((t, t), (b, 1)): (t, t),
            ((t, t), (b, b)): (t, t), ((t, 1), (t, t)): (t, t),
            ((t, 1), (t, 1)): (t, 1), ((t, 1), (t, b)): (t, 1),
            ((t, 1), (a, t)): (t, t), ((t, 1), (a, 1)): (t, 1),
            ((t, 1), (a, b)): (t, 1), ((t, 1), (b, t)): (t, t),
            ((t, 1), (b, 1)): (t, 1), ((t, 1), (b, b)): (t, 1),
            ((t, b), (t, t)): (t, t), ((t, b), (t, 1)): (t, 1),
            ((t, b), (t, b)): (t, b), ((t, b), (a, t)): (t, t),
            ((t, b), (a, 1)): (t, 1), ((t, b), (a, b)): (t, b),
            ((t, b), (b, t)): (t, t), ((t, b), (b, 1)): (t, 1),
            ((t, b), (b, b)): (t, b), ((a, t), (t, t)): (t, t),
            ((a, t), (t, 1)): (t, t), ((a, t), (t, b)): (t, t),
            ((a, t), (a, t)): (a, t), ((a, t), (a, 1)): (a, t),
            ((a, t), (a, b)): (a, t), ((a, t), (b, t)): (a, t),
            ((a, t), (b, 1)): (a, t), ((a, t), (b, b)): (a, t),
            ((a, 1), (t, t)): (t, t), ((a, 1), (t, 1)): (t, 1),
            ((a, 1), (t, b)): (t, 1), ((a, 1), (a, t)): (a, t),
            ((a, 1), (a, 1)): (a, 1), ((a, 1), (a, b)): (a, 1),
            ((a, 1), (b, t)): (a, t), ((a, 1), (b, 1)): (a, 1),
            ((a, 1), (b, b)): (a, 1), ((a, b), (t, t)): (t, t),
            ((a, b), (t, 1)): (t, 1), ((a, b), (t, b)): (t, b),
            ((a, b), (a, t)): (a, t), ((a, b), (a, 1)): (a, 1),
            ((a, b), (a, b)): (a, b), ((a, b), (b, t)): (a, t),
            ((a, b), (b, 1)): (a, 1), ((a, b), (b, b)): (a, b),
            ((b, t), (t, t)): (t, t), ((b, t), (t, 1)): (t, t),
            ((b, t), (t, b)): (t, t), ((b, t), (a, t)): (a, t),
            ((b, t), (a, 1)): (a, t), ((b, t), (a, b)): (a, t),
            ((b, t), (b, t)): (b, t), ((b, t), (b, 1)): (b, t),
            ((b, t), (b, b)): (b, t), ((b, 1), (t, t)): (t, t),
            ((b, 1), (t, 1)): (t, 1), ((b, 1), (t, b)): (t, 1),
            ((b, 1), (a, t)): (a, t), ((b, 1), (a, 1)): (a, 1),
            ((b, 1), (a, b)): (a, 1), ((b, 1), (b, t)): (b, t),
            ((b, 1), (b, 1)): (b, 1), ((b, 1), (b, b)): (b, 1),
            ((b, b), (t, t)): (t, t), ((b, b), (t, 1)): (t, 1),
            ((b, b), (t, b)): (t, b), ((b, b), (a, t)): (a, t),
            ((b, b), (a, 1)): (a, 1), ((b, b), (a, b)): (a, b),
            ((b, b), (b, t)): (b, t), ((b, b), (b, 1)): (b, 1),
            ((b, b), (b, b)): (b, b),
        }
        for a1, n1 in itertools.product(self.alphabets, self.numerals):
            l1 = self.AlphaNumeral(a1, n1)
            for a2, n2 in itertools.product(self.alphabets, self.numerals):
                l2 = self.AlphaNumeral(a2, n2)
            self.assertEqual(l1 | l2, l2 | l1)
            self.assertEqual(
                l1 | l2, self.AlphaNumeral(*join_tests[(a1, n1), (a2, n2)]))
        t, b = self.AlphaNumeral(top=True), self.AlphaNumeral(bottom=True)
        for a, n in itertools.product(self.alphabets, self.numerals):
            l = self.AlphaNumeral(a, n)
            self.assertEqual(l | t, t)
            self.assertEqual(t | l, t)
            self.assertEqual(l | b, l)
            self.assertEqual(b | l, l)
            self.assertEqual(l & t, l)
            self.assertEqual(t & l, l)
            self.assertEqual(l & b, b)
            self.assertEqual(b & l, b)
