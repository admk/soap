import unittest
import itertools

from soap.lattice import Lattice, flat, power, map


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


class _FLat(flat(int, 'IntLattice')):
    pass


class TestFlatLattice(unittest.TestCase):
    """Unittesting for :class:`soap.lattice.flat.FlatLattice`."""
    def setUp(self):
        self.bottom, self.top = _FLat(bottom=True), _FLat(top=True)

    def test_top_and_bottom(self):
        self.assertEqual(_FLat(bottom=True), _FLat(bottom=True))
        self.assertEqual(_FLat(top=True), _FLat(top=True))

    def test_join(self):
        self.assertEqual(self.bottom | self.bottom, self.bottom)
        self.assertEqual(self.bottom | _FLat(1), _FLat(1))
        self.assertEqual(_FLat(1) | self.bottom, _FLat(1))
        self.assertEqual(_FLat(1) | _FLat(2), self.top)
        self.assertEqual(_FLat(1) | self.top, self.top)
        self.assertEqual(self.top | _FLat(1), self.top)
        self.assertEqual(self.top | self.top, self.top)

    def test_meet(self):
        self.assertEqual(self.bottom & self.bottom, self.bottom)
        self.assertEqual(self.bottom & _FLat(1), self.bottom)
        self.assertEqual(_FLat(1) & self.bottom, self.bottom)
        self.assertEqual(_FLat(1) & _FLat(2), self.bottom)
        self.assertEqual(_FLat(1) & self.top, _FLat(1))
        self.assertEqual(self.top & _FLat(1), _FLat(1))
        self.assertEqual(self.top & self.top, self.top)


class _ILat(power(int)):
    pass


class TestPowerLattice(unittest.TestCase):
    """Unittesting for :class:`soap.lattice.PowerLattice`."""
    def setUp(self):
        self.ib, self.it = _ILat(bottom=True), _ILat(top=True)

    def test_infinite(self):
        self.assertEqual(self.ib | self.ib, self.ib)
        self.assertEqual(self.ib | _ILat([1]), _ILat([1]))
        self.assertEqual(_ILat([1]) | self.ib, _ILat([1]))
        self.assertEqual(_ILat([1]) | _ILat([2]), _ILat([1, 2]))
        self.assertEqual(_ILat([1]) | self.it, self.it)
        self.assertEqual(self.it | _ILat([1]), self.it)
        self.assertEqual(self.it | self.it, self.it)


class _MLat(map(str, _FLat, 'State')):
    pass


class TestMapLattice(unittest.TestCase):
    """Unittesting for :class:`soap.lattice.MapLattice`."""
    def setUp(self):
        self.val_bot = _FLat(bottom=True)
        self.val_top = _FLat(top=True)
        self.bot = _MLat(bottom=True)
        self.top = _MLat(top=True)
        self.bot_bot = _MLat({'x': self.val_bot, 'y': self.val_bot})
        self.bot_one = _MLat({'x': self.val_bot, 'y': 1})
        self.one_one = _MLat({'x': 1, 'y': 1})
        self.one_two = _MLat({'x': 1, 'y': 2})
        self.one_bot = _MLat({'x': 1})
        self.one_top = _MLat({'x': 1, 'y': self.val_top})

    def test_top_and_bottom(self):
        self.assertEqual(_MLat({}), self.bot)
        self.assertEqual(self.bot, _MLat({}))
        self.assertEqual(self.bot_bot, self.bot)
        self.assertEqual(self.bot_one, _MLat({'y': 1}))
        self.assertNotEqual(_MLat({'x': self.val_top}), self.top)

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


class _Alphabet(flat(str, name='Alphabet')):
    pass


class _Numeral(flat(int, name='Numeral')):
    pass


class _AlphaNumeral(_Alphabet * _Numeral):
    __slots__ = ()

    def __init__(self, alpha=None, numer=None, top=False, bottom=False):
        if top or bottom:
            super().__init__(top=top, bottom=bottom)
            return

        def cast(cls, v):
            if v == 'top':
                return cls(top=True)
            if v == 'bottom':
                return cls(bottom=True)
            return cls(v)

        super().__init__(cast(_Alphabet, alpha), cast(_Numeral, numer))


class TestComponentWiseLattice(unittest.TestCase):
    """Unittesting for :class:`soap.lattice.base.LatticeMeta`
    ComponentWiseLattice."""
    def setUp(self):
        self.alphabets = ['a']
        self.numerals = [1]

        self.alphabets += ['top', 'bottom']
        self.numerals += ['top', 'bottom']

    def test_top_and_bottom(self):
        self.assertEqual(
            _AlphaNumeral('top', 'top'), _AlphaNumeral(top=True))
        self.assertEqual(
            _AlphaNumeral('bottom', 'bottom'),
            _AlphaNumeral(bottom=True))

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
            l1 = _AlphaNumeral(a1, n1)
            for a2, n2 in itertools.product(self.alphabets, self.numerals):
                l2 = _AlphaNumeral(a2, n2)
                test = (a1, n1) in rel_tests[a2, n2]
                same = (a1, n1) == (a2, n2)
                if test or same:
                    self.assertLessEqual(l1, l2)
                else:
                    self.assertFalse(l1 <= l2)
        self.assertEqual(
            _AlphaNumeral(top=True), _AlphaNumeral('top', 'top'))

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
            l1 = _AlphaNumeral(a1, n1)
            for a2, n2 in itertools.product(self.alphabets, self.numerals):
                l2 = _AlphaNumeral(a2, n2)
            self.assertEqual(l1 | l2, l2 | l1)
            self.assertEqual(
                l1 | l2, _AlphaNumeral(*join_tests[(a1, n1), (a2, n2)]))
        t, b = _AlphaNumeral(top=True), _AlphaNumeral(bottom=True)
        for a, n in itertools.product(self.alphabets, self.numerals):
            l = _AlphaNumeral(a, n)
            self.assertEqual(l | t, t)
            self.assertEqual(t | l, t)
            self.assertEqual(l | b, l)
            self.assertEqual(b | l, l)
            self.assertEqual(l & t, l)
            self.assertEqual(t & l, l)
            self.assertEqual(l & b, b)
            self.assertEqual(b & l, b)
