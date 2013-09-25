import unittest
import itertools

from soap.lattice import Lattice, flat, denotational, power, map


class TestLattice(unittest.TestCase):
    """Unittesting for :class:`soap.lattice.Lattice`."""
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


class TestFlatLattice(unittest.TestCase):
    """Unittesting for :class:`soap.lattice.FlatLattice`."""
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

    def test_join(self):
        self.assertEqual(self.b | self.b, self.b)
        self.assertEqual(self.b | self.Lat(1), self.Lat(1))
        self.assertEqual(self.Lat(1) | self.b, self.Lat(1))
        self.assertEqual(self.Lat(1) | self.Lat(2), self.t)
        self.assertEqual(self.Lat(1) | self.t, self.t)
        self.assertEqual(self.t | self.Lat(1), self.t)
        self.assertEqual(self.t | self.t, self.t)

    def test_meet(self):
        self.assertEqual(self.b & self.b, self.b)
        self.assertEqual(self.b & self.Lat(1), self.b)
        self.assertEqual(self.Lat(1) & self.b, self.b)
        self.assertEqual(self.Lat(1) & self.Lat(2), self.b)
        self.assertEqual(self.Lat(1) & self.t, self.Lat(1))
        self.assertEqual(self.t & self.Lat(1), self.Lat(1))
        self.assertEqual(self.t & self.t, self.t)

    def test_from_set(self):
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
    """Unittesting for :class:`soap.lattice.PowerLattice`."""
    def setUp(self):
        self.ILat = power(int)
        self.ib, self.it = self.ILat(bottom=True), self.ILat(top=True)
        self.FLat = power([1, 2, 3])
        self.fb, self.ft = self.FLat(bottom=True), self.FLat(top=True)

    def test_infinite(self):
        self.assertEqual(self.ib | self.ib, self.ib)
        self.assertEqual(self.ib | self.ILat([1]), self.ILat([1]))
        self.assertEqual(self.ILat([1]) | self.ib, self.ILat([1]))
        self.assertEqual(self.ILat([1]) | self.ILat([2]), self.ILat([1, 2]))
        self.assertEqual(self.ILat([1]) | self.it, self.it)
        self.assertEqual(self.it | self.ILat([1]), self.it)
        self.assertEqual(self.it | self.it, self.it)


class TestComponentWiseLattice(unittest.TestCase):
    """Unittesting for :class:`soap.lattice.base.LatticeMeta`
    ComponentWiseLattice."""
    def setUp(self):
        self.alphabets = ['a']
        self.numerals = [1]
        Alphabet = flat(self.alphabets, name='Alphabet')
        Numeral = flat(self.numerals, name='Numeral')

        class AlphaNumeral(Alphabet * Numeral):
            def __init__(self, alpha=None, numer=None,
                         top=False, bottom=False):
                if top or bottom:
                    super().__init__(top=top, bottom=bottom)
                    return

                def cast(cls, v):
                    if v == 'top':
                        return cls(top=True)
                    if v == 'bottom':
                        return cls(bottom=True)
                    return cls(v)

                super().__init__(cast(Alphabet, alpha), cast(Numeral, numer))

        self.AlphaNumeral = AlphaNumeral
        self.alphabets += ['top', 'bottom']
        self.numerals += ['top', 'bottom']

    def test_top_and_bottom(self):
        self.assertEqual(
            self.AlphaNumeral('top', 'top'), self.AlphaNumeral(top=True))
        self.assertEqual(
            self.AlphaNumeral('bottom', 'bottom'),
            self.AlphaNumeral(bottom=True))

    def test_order(self):
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
                if test or same:
                    self.assertLessEqual(l1, l2)
                else:
                    self.assertFalse(l1 <= l2)
        self.assertEqual(
            self.AlphaNumeral(top=True), self.AlphaNumeral('top', 'top'))

    def test_join_and_meet(self):
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


class TestSummationLattice(unittest.TestCase):
    def setUp(self):
        raise unittest.SkipTest


class TestMapLattice(unittest.TestCase):
    """Unittesting for :class:`soap.lattice.MapLattice`."""
    def setUp(self):
        self.Lat = map(str, flat(int, 'Int'), 'State')
        self.bot = self.Lat(bottom=True)
        self.top = self.Lat(top=True)
        self.bot_bot = self.Lat({'x': 'bottom', 'y': 'bottom'})
        self.bot_one = self.Lat({'x': 'bottom', 'y': 1})
        self.one_one = self.Lat({'x': 1, 'y': 1})
        self.one_two = self.Lat({'x': 1, 'y': 2})
        self.one_bot = self.Lat({'x': 1})
        self.one_top = self.Lat({'x': 1, 'y': 'top'})

    def test_top_and_bottom(self):
        self.assertEqual(self.Lat({}), self.bot)
        self.assertEqual(self.bot, self.Lat({}))
        self.assertEqual(self.bot_bot, self.bot)
        self.assertEqual(self.bot_one, self.Lat({'y': 1}))
        self.assertNotEqual(self.Lat({'x': 'top'}), self.top)

    def test_order(self):
        self.assertTrue(self.bot_one <= self.one_one)
        self.assertFalse(self.one_one <= self.bot_one)
        self.assertFalse(self.one_one <= self.one_two)
        self.assertFalse(self.one_two <= self.one_one)
        self.assertTrue(self.one_bot <= self.one_one)
        self.assertFalse(self.one_one <= self.one_bot)
        self.assertFalse(self.one_bot <= self.bot_one)
        self.assertFalse(self.bot_one <= self.one_bot)

    def test_join(self):
        self.assertEqual(self.bot_bot | self.bot, self.bot)
        self.assertEqual(self.bot_bot | self.top, self.top)
        self.assertEqual(self.one_bot | self.bot_one, self.one_one)
        self.assertEqual(self.one_one | self.one_two, self.one_top)

    def test_meet(self):
        self.assertEqual(self.bot_bot & self.bot, self.bot)
        self.assertEqual(self.bot_bot & self.top, self.bot)
        self.assertEqual(self.one_bot & self.bot_one, self.bot)
        self.assertEqual(self.one_one & self.one_two, self.one_bot)


class TestDenotational(unittest.TestCase):
    """Unittesting for :class:`soap.lattice.denotational`."""
    def setUp(self):
        self.Val = denotational(int, 'IntDenotational')
        self.bot = self.Val(bottom=True)
        self.v1 = self.Val(1)
        self.v2 = self.Val(2)
        self.v3 = self.Val(3)

    def test_operators(self):
        self.assertEqual(self.v1 + self.v2, self.v3)
        self.assertEqual(self.bot + self.v1, self.bot)
        self.assertEqual(self.v1 + self.bot, self.bot)
        self.assertEqual(1 + self.bot, self.bot)
        self.assertEqual(self.bot + 1, self.bot)
        self.assertEqual(1 + self.v2, self.v3)
        self.assertEqual(self.v2 + 1, self.v3)
        self.assertEqual(self.v2 - self.v1, self.v1)
        self.assertEqual(self.bot - self.v1, self.bot)
        self.assertEqual(self.v1 - self.bot, self.bot)
        self.assertEqual(1 - self.bot, self.bot)
        self.assertEqual(self.bot - 1, self.bot)
        self.assertEqual(2 - self.v1, self.v1)
        self.assertEqual(self.v2 - 1, self.v1)
