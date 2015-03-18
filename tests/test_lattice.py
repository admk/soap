import unittest

from soap.lattice import Lattice


class TestLattice(unittest.TestCase):
    """Unittesting for :class:`soap.lattice.base.Lattice`."""
    def setUp(self):
        self.bottom = Lattice(bottom=True)
        self.top = Lattice(top=True)

    def test_top_and_bottom(self):
        self.assertEqual(self.bottom, Lattice(bottom=True))
        self.assertEqual(self.top, Lattice(top=True))
        self.assertNotEqual(Lattice(bottom=True), Lattice(top=True))

    def test_order(self):
        self.assertIs(self.bottom <= self.bottom, True)
        self.assertIs(self.bottom >= self.bottom, True)
        self.assertIs(self.bottom <= self.top, True)
        self.assertIs(self.bottom >= self.top, False)
        self.assertIs(self.top <= self.bottom, False)
        self.assertIs(self.top >= self.bottom, True)
        self.assertIs(self.top <= self.top, True)
        self.assertIs(self.top >= self.top, True)
