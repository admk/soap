import unittest

from soap.semantics import ClassicalState
from soap.expr import Expr


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
        self.assertEqual(self.one.conditional(Expr('x < 1'), True), self.bot)
        self.assertEqual(self.one.conditional(Expr('x > 1'), True), self.bot)
        self.assertEqual(self.one.conditional(Expr('x < 2'), True), self.one)
