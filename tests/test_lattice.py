import unittest
import itertools

from soap.semantics.lattice import Lattice, bottom, top, flat


class TestLattice(unittest.TestCase):
    """Unittesting for :class:`soap.semantics.Lattice`."""
    def setUp(self):
        pass

    def test_top_and_bottom(self):
        class AltLattice(Lattice):
            pass
        self.assertNotEqual(bottom(AltLattice), bottom(Lattice))
        self.assertEqual(bottom(Lattice), bottom(Lattice))
        self.assertEqual(top(Lattice), top(Lattice))
        self.assertNotEqual(bottom(Lattice), top(Lattice))

    def test_flat_lattice_join(self):
        IntLattice = flat(int)
        b, t = bottom(IntLattice), top(IntLattice)
        self.assertEqual(b | b, b)
        self.assertEqual(b | IntLattice(1), IntLattice(1))
        self.assertEqual(IntLattice(1) | b, IntLattice(1))
        self.assertEqual(IntLattice(1) | IntLattice(2), t)
        self.assertEqual(IntLattice(1) | t, t)
        self.assertEqual(t | IntLattice(1), t)
        self.assertEqual(t | t, t)

    def test_flat_lattice_meet(self):
        IntLattice = flat(int)
        b, t = bottom(IntLattice), top(IntLattice)
        self.assertEqual(b & b, b)
        self.assertEqual(b & IntLattice(1), b)
        self.assertEqual(IntLattice(1) & b, b)
        self.assertEqual(IntLattice(1) & IntLattice(2), b)
        self.assertEqual(IntLattice(1) & t, IntLattice(1))
        self.assertEqual(t & IntLattice(1), IntLattice(1))
        self.assertEqual(t & t, t)

    def test_flat_lattice_from_set(self):
        Flat = flat([1, 2, 3])
        b, t = bottom(Flat), top(Flat)
        self.assertEqual(Flat(1), Flat(1))
        self.assertNotEqual(Flat(1), Flat(2))
        self.assertNotEqual(Flat(1), b)
        self.assertNotEqual(Flat(1), t)
        self.assertEqual(b | Flat(1), Flat(1))
        self.assertEqual(t | Flat(1), t)
        self.assertEqual(Flat(1) | b, Flat(1))
        self.assertEqual(Flat(1) | t, t)
        self.assertEqual(Flat(1) | Flat(2), t)
        self.assertEqual(b & Flat(1), b)
        self.assertEqual(t & Flat(1), Flat(1))
        self.assertEqual(Flat(1) & b, b)
        self.assertEqual(Flat(1) & t, Flat(1))
        self.assertEqual(Flat(1) & Flat(2), b)
        with self.assertRaises(ValueError):
            Flat(4)

    def test_component_wise_lattice(self):
        alphabets = ['a']
        numerals = [1]
        FlatAlp = flat(alphabets, name='Alphabet')
        FlatNum = flat(numerals, name='Numeral')
        CombLattice = FlatAlp * FlatNum
        alphabets += ['top', 'bottom']
        numerals += ['top', 'bottom']
        rel_tests = {
            ('top', 'top'): [
                ('top', 1),
                ('top', 'bottom'),
                ('a', 'top'),
                ('a', 1),
                ('a', 'bottom'),
                ('bottom', 'top'),
                ('bottom', 1),
                ('bottom', 'bottom'),
            ],
            ('top', 1): [
                ('top', 'bottom'),
                ('a', 1),
                ('a', 'bottom'),
                ('bottom', 1),
                ('bottom', 'bottom'),
            ],
            ('top', 'bottom'): [
                ('a', 'bottom'),
                ('bottom', 'bottom'),
            ],
            ('a', 'top'): [
                ('a', 1),
                ('a', 'bottom'),
                ('bottom', 'top'),
                ('bottom', 1),
                ('bottom', 'bottom'),
            ],
            ('a', 1): [
                ('a', 'bottom'),
                ('bottom', 1),
                ('bottom', 'bottom'),
            ],
            ('a', 'bottom'): [
                ('bottom', 'bottom'),
            ],
            ('bottom', 'top'): [
                ('bottom', 1),
                ('bottom', 'bottom'),
            ],
            ('bottom', 1): [
                ('bottom', 'bottom'),
            ],
            ('bottom', 'bottom'): [],
        }
        for a1, n1 in itertools.product(alphabets, numerals):
            l1 = CombLattice(a1, n1)
            for a2, n2 in itertools.product(alphabets, numerals):
                l2 = CombLattice(a2, n2)
                test = (a2, n2) in rel_tests[a1, n1]
                same = (a1, n1) == (a2, n2)
                self.assertEqual(l2 <= l1, test or same)
        self.assertEqual(top(CombLattice), CombLattice('top', 'top'))
