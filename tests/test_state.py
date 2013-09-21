import unittest

from soap.semantics import ClassicalState, IntervalState
from soap.expr import Expr, BoolExpr


class TestClassicalState(unittest.TestCase):
    """Unittesting for :class:`soap.semantics.ClassicalState`."""
    def setUp(self):
        self.bot = ClassicalState(bottom=True)
        self.top = ClassicalState(top=True)
        self.one = ClassicalState({'x': 1})
        self.two = ClassicalState({'x': 2})

    def test_assign(self):
        self.assertEqual(self.bot.assign('x', Expr('x + 1')), self.bot)
        self.assertEqual(self.one.assign('x', Expr('x + 1')), self.two)

    def test_conditional(self):
        self.assertEqual(
            self.one.conditional(BoolExpr('x < 1'), True), self.bot)
        self.assertEqual(
            self.one.conditional(BoolExpr('x > 1'), True), self.bot)
        self.assertEqual(
            self.one.conditional(BoolExpr('x < 2'), True), self.one)


class TestIntervalState(unittest.TestCase):
    """Unittesting for :class:`soap.semantics.IntervalState`."""
    def setUp(self):
        self.bot = IntervalState(bottom=True)
        self.top = IntervalState(top=True)
        self.one_three = IntervalState({'x': [1, 3]})
        self.two_four = IntervalState({'x': [2, 4]})

    def test_assign(self):
        self.assertEqual(self.bot.assign('x', Expr('x + 1')), self.bot)
        self.assertEqual(
            self.one_three.assign('x', Expr('x + 1')), self.two_four)

    def test_conditional(self):
        self.assertEqual(
            self.one_three.conditional(BoolExpr('x < 0'), True),
            self.bot)
        self.assertEqual(
            self.one_three.conditional(BoolExpr('x < 0'), False),
            self.one_three)
        self.assertEqual(
            self.one_three.conditional(BoolExpr('x < 1'), True),
            IntervalState({'x': 1}))
        self.assertEqual(
            self.one_three.conditional(BoolExpr('x < 1'), False),
            self.one_three)
        self.assertEqual(
            self.one_three.conditional(BoolExpr('x < 2'), True),
            IntervalState({'x': [1, 2]}))
        self.assertEqual(
            self.one_three.conditional(BoolExpr('x < 2'), False),
            IntervalState({'x': [2, 3]}))
