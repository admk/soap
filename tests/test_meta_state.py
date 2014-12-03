import unittest

from soap.expression.fixpoint import FixExpr
from soap.expression.linalg import AccessExpr, UpdateExpr
from soap.parser.program import parse
from soap.semantics.state.meta import MetaState


class TestMetaState(unittest.TestCase):
    def setUp(self):
        self.bot = MetaState(bottom=True)

    def test_visit_IdentityFlow(self):
        bot = self.bot.visit_IdentityFlow(parse('skip;'))
        self.assertEqual(bot, self.bot)

    def test_visit_AssignFlow(self):
        flow = parse('z := x * y;')
        state = MetaState(x='x + 1', y='y + 2').visit_AssignFlow(flow)
        compare_state = MetaState(x='x + 1', y='y + 2', z='(x + 1) * (y + 2)')
        self.assertEqual(state, compare_state)

    def test_visit_IfFlow(self):
        flow = parse('if (x < n) (x := x + 1;) (x := x - 1;);')
        state = MetaState(x='y', n='n').visit_IfFlow(flow)
        compare_state = MetaState(x='y < n ? y + 1 : y - 1', n='n')
        self.assertEqual(state, compare_state)

    def test_visit_WhileFlow(self):
        flow = parse('while (x < n) (x := x + 1;);')
        init_state = MetaState(x='x', n='n', y='y')
        state = init_state.visit_WhileFlow(flow)
        fix_expr = FixExpr(
            parse('(x < n)'), MetaState(x='x + 1', y='y', n='n'), parse('x'),
            init_state)
        compare_state = MetaState(x=fix_expr, y='y', n='n')
        self.assertEqual(state, compare_state)

    def test_visit_CompositionalFlow(self):
        flow = parse('x := x + 1; x := x * 2;')
        state = MetaState(x='x').visit_CompositionalFlow(flow)
        compare_state = MetaState(x='(x + 1) * 2')
        self.assertEqual(state, compare_state)

    def test_access_expr(self):
        flow = parse('x := y[i];')
        state = MetaState(x='x', y='y', i='i').visit_AssignFlow(flow)
        compare_state = MetaState(
            x=AccessExpr(parse('y'), [parse('i')]), y='y', i='i')
        self.assertEqual(state, compare_state)

    def test_update_expr(self):
        flow = parse('x[i] := 1;')
        state = MetaState(x='x', i='i').visit_AssignFlow(flow)
        compare_state = MetaState(
            x=UpdateExpr(parse('x'), [parse('i')], parse('1')), y='y')
        self.assertEqual(state, compare_state)
