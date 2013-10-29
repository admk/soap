import unittest

from soap.semantics import BoxState
from soap.expression import Expr, BoolExpr


class TestBoxState(unittest.TestCase):
    """Unittesting for :class:`soap.semantics.BoxState`."""
    def setUp(self):
        self.bot = BoxState(bottom=True)
        self.top = BoxState(top=True)
        self.one_three = BoxState({'x': [1, 3]})
        self.two_four = BoxState({'x': [2, 4]})

    def test_assign(self):
        self.assertEqual(self.bot.assign('x', Expr('x + 1')), self.bot)
        self.assertEqual(
            self.one_three.assign('x', Expr('x + 1')), self.two_four)

    def test_conditional(self):
        self.assertEqual(
            self.one_three.conditional(BoolExpr('x < 1'), True),
            self.bot)
        self.assertEqual(
            self.one_three.conditional(BoolExpr('x < 1'), False),
            self.one_three)
        self.assertEqual(
            self.one_three.conditional(BoolExpr('x < 2'), True),
            BoxState({'x': 1}))
        self.assertEqual(
            self.one_three.conditional(BoolExpr('x < 2'), False),
            BoxState({'x': [2, 3]}))
        self.assertEqual(
            self.one_three.conditional(BoolExpr('x < 3'), True),
            BoxState({'x': [1, 2]}))
        self.assertEqual(
            self.one_three.conditional(BoolExpr('x < 3'), False),
            BoxState({'x': 3}))
        self.assertEqual(
            self.bot.conditional(BoolExpr('x < 3'), True), self.bot)
        self.assertEqual(
            self.bot.conditional(BoolExpr('x < 3'), False), self.bot)
