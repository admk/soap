import unittest

from soap.expression import expr
from soap.label import Identifier, Annotation
from soap.semantics.state import IdentifierBoxState
from soap.semantics.error import ErrorSemantics


class TestIdentifierBoxState(unittest.TestCase):
    """Unittesting for :class:`soap.semantics.BoxState`."""
    def setUp(self):
        self.bot = IdentifierBoxState(bottom=True)
        self.top = IdentifierBoxState(top=True)
        self.ann_bot = Annotation(bottom=True)
        self.ann_top = Annotation(top=True)

    def test_init(self):
        current_identifier = Identifier(expr('x'), annotation=self.ann_bot)
        error = ErrorSemantics(['1.0', '3.0'])
        state = IdentifierBoxState({'x': error})
        self.assertEqual(state['x'], error)
        self.assertEqual(state[current_identifier], error)

    def test_getter_and_setter(self):
        raise NotImplementedError

    def test_iteration_increment(self):
        raise NotImplementedError

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
