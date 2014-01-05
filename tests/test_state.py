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
        self.s13 = IdentifierBoxState(x=[1, 3])
        self.ann_top = Annotation(top=True)
        x = expr('x')
        self.ann = Annotation(Label(x), Iteration(bottom=True))
        self.curr_id = Identifier(x, annotation=Annotation(bottom=True))
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
        s24 = self.s13.assign(expr('x'), expr('x + 1'), self.ann)
        self.assertEqual(s24[self.curr_id], expr('[2, 4]'))
        self.assertEqual(s24[self.ann_id], expr('[2, 4]'))
        self.assertTrue(s24[self.ann_id.prev_iteration()].is_bottom())
        s35 = s24.assign(expr('x'), expr('x + 1'), self.ann)
        self.assertEqual(s35[self.curr_id], expr('[3, 5]'))
        self.assertEqual(s35[self.ann_id.prev_iteration()], expr('[2, 4]'))

    def test_assign_bottom_and_top(self):
        bot = self.bot.assign(expr('x'), expr('x + 1'), self.ann)
        self.assertEqual(self.bot, bot)
        top = self.top.assign(expr('x'), expr('x + 1'), self.ann)
        self.assertEqual(self.top, top)

    def test_conditional(self):
        self.assertEqual(
            self.s13.conditional(expr('x < 1'), True, self.ann), self.bot)
        self.assertEqual(
            self.s13.conditional(expr('x < 1'), False, self.ann),
            self.s13.assign(expr('x'), expr('[1, 3]'), self.ann))
        self.assertEqual(
            self.s13.conditional(expr('x < 2'), True, self.ann),
            self.s13.assign(expr('x'), expr('1'), self.ann))
        self.assertEqual(
            self.s13.conditional(expr('x < 2'), False, self.ann),
            self.s13.assign(expr('x'), expr('[2, 3]'), self.ann))
        self.assertEqual(
            self.s13.conditional(expr('x < 3'), True, self.ann),
            self.s13.assign(expr('x'), expr('[1, 2]'), self.ann))
        self.assertEqual(
            self.s13.conditional(expr('x < 3'), False, self.ann),
            self.s13.assign(expr('x'), expr('3'), self.ann))

    def test_conditional_bottom_and_top(self):
        self.assertEqual(
            self.bot.conditional(expr('x < 3'), True, self.ann), self.bot)
        self.assertEqual(
            self.bot.conditional(expr('x < 3'), False, self.ann), self.bot)
        self.assertEqual(
            self.top.conditional(expr('x < 3'), True, self.ann), self.top)
        self.assertEqual(
            self.top.conditional(expr('x < 3'), False, self.ann), self.top)
