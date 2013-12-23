import unittest

from soap.expression import expr
from soap.common.label import Label
from soap.semantics.state import BoxState


class TestBoxState(unittest.TestCase):
    """Unittesting for :class:`soap.semantics.BoxState`."""
    def setUp(self):
        self.bot = BoxState(bottom=True)
        self.top = BoxState(top=True)
        self.one_three = BoxState({'x': [1, 3]})
        self.two_four = BoxState({'x': [2, 4]})
        self.lab = Label()

    def test_assign(self):
        self.assertEqual(
            self.bot.assign(expr('x'), expr('x + 1'), self.lab),
            self.bot)
        self.assertEqual(
            self.one_three.assign(expr('x'), expr('x + 1'), self.lab),
            self.two_four)

    def test_conditional(self):
        self.assertEqual(
            self.one_three.conditional(expr('x < 1'), True, self.lab),
            self.bot)
        self.assertEqual(
            self.one_three.conditional(expr('x < 1'), False, self.lab),
            self.one_three)
        self.assertEqual(
            self.one_three.conditional(expr('x < 2'), True, self.lab),
            BoxState({'x': 1}))
        self.assertEqual(
            self.one_three.conditional(expr('x < 2'), False, self.lab),
            BoxState({'x': [2, 3]}))
        self.assertEqual(
            self.one_three.conditional(expr('x < 3'), True, self.lab),
            BoxState({'x': [1, 2]}))
        self.assertEqual(
            self.one_three.conditional(expr('x < 3'), False, self.lab),
            BoxState({'x': 3}))
        self.assertEqual(
            self.bot.conditional(expr('x < 3'), True, self.lab),
            self.bot)
        self.assertEqual(
            self.bot.conditional(expr('x < 3'), False, self.lab),
            self.bot)
