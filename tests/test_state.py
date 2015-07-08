import unittest

from soap.datatype import int_type
from soap.expression import (
    operators, Variable, BinaryArithExpr, BinaryBoolExpr,
)
from soap.program import (
    SkipFlow, AssignFlow, IfFlow, WhileFlow, ForFlow, CompositionalFlow
)
from soap.parser.program import parse
from soap.semantics import BoxState, IntegerInterval, ErrorSemantics


class TestBoxState(unittest.TestCase):
    def setUp(self):
        self.x = Variable('x', int_type)
        self.y = Variable('y', int_type)
        self.xl2 = BinaryBoolExpr(
            operators.LESS_OP, self.x, IntegerInterval(2))
        self.xp1 = BinaryArithExpr(
            operators.ADD_OP, self.x, IntegerInterval(1))
        self.xm1 = BinaryArithExpr(
            operators.SUBTRACT_OP, self.x, IntegerInterval(1))

    def test_visit_SkipFlow(self):
        flow = SkipFlow()
        state = BoxState(x=[1, 2])
        self.assertEqual(state.visit_SkipFlow(flow), state)

    def test_visit_AssignFlow(self):
        flow = AssignFlow(self.y, self.xp1)
        state = BoxState(x=[1, 2])
        self.assertEqual(
            state.visit_AssignFlow(flow), BoxState(x=[1, 2], y=[2, 3]))

    def test_visit_IfFlow(self):
        flow = IfFlow(
            self.xl2,
            AssignFlow(self.x, self.xp1),
            AssignFlow(self.x, self.xm1))
        state = BoxState(x=[1, 3])
        self.assertEqual(state.visit_IfFlow(flow), BoxState(x=[1, 2]))

    def test_visit_WhileFlow(self):
        flow = WhileFlow(self.xl2, AssignFlow(self.x, self.xp1))
        state = BoxState(x=[1, 4])
        self.assertEqual(state.visit_WhileFlow(flow), BoxState(x=[2, 4]))

    def test_visit_ForFlow(self):
        loop_flow = AssignFlow(self.y, BinaryArithExpr(
            operators.ADD_OP, self.y, self.x))
        state = BoxState(x=[1, 4], y=1)
        flow = ForFlow(
            SkipFlow(), self.xl2, AssignFlow(self.x, self.xp1), loop_flow)
        compare_state = BoxState(x=[2, 4], y=[1, 2])
        self.assertEqual(state.visit_ForFlow(flow), compare_state)

    def test_compositional_flow(self):
        flow = CompositionalFlow()
        flow += AssignFlow(self.x, self.xp1)
        flow += AssignFlow(self.x, self.xm1)
        state = BoxState(x=[1, 4])
        self.assertEqual(state.visit_CompositionalFlow(flow), state)


class TestBoxStateExampleTransitions(unittest.TestCase):
    """Unittesting for :class:`soap.program.flow`."""
    def setUp(self):
        self.simple_if = """
            #pragma soap output x
            int x = 0;
            if (x <= 1)
                x = x + 1;
            else
                x = x - 1;
            """
        self.simple_while = """
            #pragma soap output x
            int x = 0;
            while (x < 5)
                x = x + 1;
            """
        self.factorial = """
            #pragma soap input int x = [0, 5], int y = [0, 2]
            #pragma soap output y
            while (x <= 3) {
                y = y * x;
                x = x + 1;
            }
            """
        self.fixpoint = """
            #pragma soap input float x = [0.0, 9.0]
            #pragma soap output x
            while (x > 1)
                x = 0.9 * x;
            """

    def test_simple_if(self):
        env = BoxState(bottom=True)
        flow_env = parse(self.simple_if).flow(env)
        expect_env = BoxState(x=1)
        self.assertEqual(flow_env, expect_env)

    def test_simple_while(self):
        env = BoxState(bottom=True)
        flow_env = parse(self.simple_while).flow(env)
        expect_env = BoxState(x=5)
        self.assertEqual(flow_env, expect_env)

    def test_interval_flow(self):
        env = BoxState(x=[0, 5], y=[0, 2])
        flow_env = parse(self.factorial).flow(env)
        less_env = BoxState(x=[4, 5], y=[0, 12])
        self.assertLessEqual(less_env, flow_env)

    def test_fixpoint_flow(self):
        env = BoxState(x=[0.0, 9.0])
        flow_env = parse(self.fixpoint).flow(env)
        more_env = BoxState(x=ErrorSemantics([0.0, 1.0], [-0.01, 0.01]))
        self.assertLessEqual(flow_env, more_env)
