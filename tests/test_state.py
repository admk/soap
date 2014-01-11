import unittest

from soap.expression import expr, operators
from soap.label import Identifier, Annotation, Label, Iteration
from soap.semantics.state.box import IdentifierBoxState
from soap.semantics.state.expression import IdentifierExpressionState
from soap.semantics.error import cast


class TestIdentifierBoxState(unittest.TestCase):
    """Unittesting for :class:`soap.semantics.state.IdentifierBoxState`."""
    def setUp(self):
        self.bot = IdentifierBoxState(bottom=True)
        self.top = IdentifierBoxState(top=True)
        self.s13 = IdentifierBoxState(x=[1, 3])
        self.ann_top = Annotation(top=True)
        x = expr('x')
        self.ann = Annotation(Label(x), Iteration(bottom=True))
        self.bot_id = Identifier(x, annotation=Annotation(bottom=True))
        self.ann_id = Identifier(x, annotation=self.ann)
        self.err1 = cast(1)
        self.err2 = cast(2)

    def test_init(self):
        state1 = IdentifierBoxState({'x': self.err1})
        state2 = IdentifierBoxState(x=self.err1)
        self.assertEqual(state1, state2)
        self.assertEqual(state1['x'], self.err1)
        self.assertEqual(state1[self.bot_id], self.err1)

    def test_getter_and_setter(self):
        """Tests the transformation of state keys and values.  """
        state = IdentifierBoxState()
        state[self.ann_id] = 1
        self.assertEqual(state[self.ann_id], self.err1)
        state['x'] = 1
        self.assertEqual(state['x'], self.err1)
        self.assertEqual(state[self.bot_id], self.err1)

    def test_iterations(self):
        state = IdentifierBoxState()
        state = state.increment(self.ann_id, self.err1)
        self.assertEqual(state[self.ann_id], self.err1)
        self.assertEqual(state[self.bot_id], self.err1)
        state = state.increment(self.ann_id, self.err2)
        self.assertEqual(state[self.ann_id], self.err2)
        self.assertEqual(state[self.bot_id], self.err2)
        self.assertEqual(state[self.ann_id.prev_iteration()], self.err1)

    def test_assign(self):
        s24 = self.s13.assign(expr('x'), expr('x + 1'), self.ann)
        self.assertEqual(s24[self.bot_id], expr('[2, 4]'))
        self.assertEqual(s24[self.ann_id], expr('[2, 4]'))
        self.assertTrue(s24[self.ann_id.prev_iteration()].is_bottom())
        s35 = s24.assign(expr('x'), expr('x + 1'), self.ann)
        self.assertEqual(s35[self.bot_id], expr('[3, 5]'))
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


class TestIdentifierExpressionState(unittest.TestCase):
    """Unittesting for :class:`soap.semantics.state.IdentifierExpressionState`.
    """
    def assertExprOpArgs(self, expr, op, args):
        self.assertEqual(expr.op, op)
        if op not in operators.COMMUTATIVITY_OPERATORS:
            self.assertEqual(expr.args, tuple(args))
            return
        self.assertEqual(len(expr.args), len(args))
        for a in args:
            self.assertIn(a, expr.args)

    def setUp(self):
        self.bot = IdentifierExpressionState(bottom=True)
        self.top = IdentifierExpressionState(top=True)
        self.ann_top = Annotation(top=True)
        x = expr('x')
        self.ann = Annotation(Label(x), Iteration(bottom=True))
        self.bot_id = Identifier(x, annotation=Annotation(bottom=True))
        self.top_id = Identifier(x, annotation=Annotation(top=True))
        self.ann_id = Identifier(x, annotation=self.ann)

    def test_init(self):
        state1 = IdentifierExpressionState({self.bot_id: expr('x + 1')})
        state2 = IdentifierExpressionState(x=expr('x + 1'))
        state3 = IdentifierExpressionState()
        state3[self.bot_id] = expr('x + 1')
        self.assertEqual(state1, state2)
        self.assertEqual(state1, state3)
        self.assertExprOpArgs(
            state1[self.bot_id], operators.ADD_OP, [self.top_id, expr('1')])

    def test_getter_and_setter(self):
        """Tests the transformation of state keys and values.  """
        state = IdentifierExpressionState()
        state[self.ann_id] = 'x + 1'
        self.assertExprOpArgs(
            state[self.ann_id], operators.ADD_OP, [self.top_id, expr('1')])

        state = IdentifierExpressionState()
        state['x'] = 'x + 1'
        self.assertExprOpArgs(
            state['x'], operators.ADD_OP, [self.top_id, expr('1')])
        self.assertExprOpArgs(
            state[self.bot_id], operators.ADD_OP, [self.top_id, expr('1')])

    def test_iteration(self):
        state = IdentifierExpressionState()
        state = state.increment(self.ann_id, expr('x + 1'))
        self.assertExprOpArgs(
            state[self.ann_id], operators.ADD_OP, [self.top_id, expr('1')])
        self.assertEqual(state[self.bot_id], self.ann_id)

        state = state.increment(self.ann_id, expr('x * 2'))
        self.assertExprOpArgs(
            state[self.ann_id], operators.MULTIPLY_OP,
            [self.ann_id.prev_iteration(), expr('2')])
        self.assertEqual(state[self.bot_id], self.ann_id)
        self.assertExprOpArgs(
            state[self.ann_id.prev_iteration()], operators.ADD_OP,
            [self.top_id, expr('1')])

    def test_assign(self):
        state = IdentifierExpressionState()

        state1 = state.assign(expr('x'), expr('x + 1'), self.ann)
        state2 = state.increment(self.ann_id, expr('x + 1'))
        self.assertEqual(state1, state2)

        state1 = state1.assign(expr('x'), expr('x * 2'), self.ann)
        state2 = state2.increment(self.ann_id, expr('x + 1'))
        self.assertEqual(state1, state2)

    def test_conditional(self):
        pass
