import unittest

from soap.expression import expr
from soap.label import Identifier, Annotation, Label, Iteration
from soap.semantics.state.box import IdentifierBoxState
from soap.semantics.error import cast


class TestIdentifierBoxState(unittest.TestCase):
    """Unittesting for :class:`soap.semantics.BoxState`."""
    def setUp(self):
        self.bot = IdentifierBoxState(bottom=True)
        self.top = IdentifierBoxState(top=True)
        self.one_three = IdentifierBoxState(x=[1, 3])
        self.ann_bot = Annotation(bottom=True)
        self.ann_top = Annotation(top=True)
        x = expr('x')
        self.ann = Annotation(Label(x), Iteration(bottom=True))
        self.curr_id = Identifier(x, annotation=self.ann_bot)
        self.ann_id = Identifier(x, annotation=self.ann)
        self.err1 = cast(1)
        self.err2 = cast(2)

    def test_init(self):
        state1 = IdentifierBoxState({'x': self.err1})
        state2 = IdentifierBoxState(x=self.err1)
        self.assertEqual(state1, state2)
        self.assertEqual(state1['x'], self.err1)
        self.assertEqual(state1[self.curr_id], self.err1)

    def test_getter_and_setter(self):
        """Tests the transformation of state keys and values.  """
        state = IdentifierBoxState()
        state[self.ann_id] = self.err1
        self.assertEqual(state['x'], self.err1)
        self.assertEqual(state[self.ann_id], self.err1)
        self.assertEqual(state[self.curr_id], self.err1)

    def test_iterations(self):
        state = IdentifierBoxState()
        state[self.ann_id] = self.err1
        self.assertEqual(state[self.ann_id], self.err1)
        self.assertEqual(state[self.curr_id], self.err1)
        state[self.ann_id] = self.err2
        self.assertEqual(state[self.ann_id], self.err2)
        self.assertEqual(state[self.curr_id], self.err2)
        self.assertEqual(state[self.ann_id.prev_iteration()], self.err1)

    def test_assign(self):
        bot = self.bot.assign(expr('x'), expr('x + 1'), self.ann)
        self.assertEqual(self.bot, bot)
        two_four = self.one_three.assign(expr('x'), expr('x + 1'), self.ann)
        self.assertEqual(two_four[self.curr_id], cast([2, 4]))
        self.assertEqual(two_four[self.ann_id], cast([2, 4]))
        self.assertTrue(two_four[self.ann_id.prev_iteration()].is_bottom())
        three_five = two_four.assign(expr('x'), expr('x + 1'), self.ann)
        self.assertEqual(three_five[self.curr_id], cast([3, 5]))
        self.assertEqual(
            three_five[self.ann_id.prev_iteration()], cast([2, 4]))

    def test_conditional(self):
        return
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
