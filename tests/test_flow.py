import unittest

from akpytemp.utils import code_gobble

from soap.program import (
    IdentityFlow, AssignFlow, IfFlow, WhileFlow, CompositionalFlow
)
from soap.parser.program import parse
from soap.semantics import BoxState


class TestIdentityFlow(unittest.TestCase):
    """Unittesting for :class:`soap.program.IdentityFlow`."""
    def setUp(self):
        self.flow = IdentityFlow()
        self.state = BoxState(x=[1, 2])

    def test_flow(self):
        self.assertEqual(self.flow.flow(self.state), self.state)


class TestAssignFlow(unittest.TestCase):
    """Unittesting for :class:`soap.program.AssignFlow`."""
    def setUp(self):
        self.flow = AssignFlow(parse('y'), parse('x'))
        self.expr_flow = AssignFlow(parse('x'), parse('x + 1'))
        self.state = BoxState(x=[1, 2])

    def test_flow(self):
        self.assertEqual(
            self.flow.flow(self.state), BoxState(x=[1, 2], y=[1, 2]))
        self.assertEqual(self.expr_flow.flow(self.state), BoxState(x=[2, 3]))


class TestIfFlow(unittest.TestCase):
    """Unittesting for :class:`soap.program.IfFlow`."""
    def setUp(self):
        self.flow = IfFlow(
            parse('x < 2'),
            AssignFlow(parse('x'), parse('x + 1')),
            AssignFlow(parse('x'), parse('x - 1')))
        self.state = BoxState(x=[1, 3])

    def test_flow(self):
        self.assertEqual(self.flow.flow(self.state), BoxState(x=[1, 2]))


class TestWhileFlow(unittest.TestCase):
    """Unittesting for :class:`soap.program.WhileFlow`."""
    def setUp(self):
        self.flow = WhileFlow(
            parse('x < 3'), AssignFlow(parse('x'), parse('x + 1')))
        self.state = BoxState(x=[1, 4])

    def test_flow(self):
        self.assertEqual(self.flow.flow(self.state), BoxState(x=[3, 4]))


class TestCompositionalFlow(unittest.TestCase):
    """Unittesting for :class:`soap.program.CompositionalFlow`."""
    def setUp(self):
        self.flow = CompositionalFlow()
        self.flow += AssignFlow(parse('x'), parse('x + 1'))
        self.flow += AssignFlow(parse('x'), parse('x - 1'))
        self.state = BoxState(x=[1, 4])

    def test_flow(self):
        self.assertEqual(self.flow.flow(self.state), self.state)


class TestExampleFlow(unittest.TestCase):
    """Unittesting for :class:`soap.program.flow`."""
    def setUp(self):
        self.simple_if = code_gobble(
            """
            x := 0;
            if (x <= 1) (
                x := x + 1;
            ) (
                x := x - 1;
            );
            """)
        self.simple_while = code_gobble(
            """
            x := 0;
            while (x < 5) (
                x := x + 1;
            );
            """)
        self.factorial = code_gobble(
            """
            while (x <= 3) (
                y := y * x;
                x := x + 1;
            );
            """)
        self.fixpoint = code_gobble(
            """
            while (x > 1) (
                x := 0.9 * x;
            );
            """)
        self.newton = code_gobble(
            """
            x0 := 0.0;
            i := 0;
            while (x > x0) (
                i := i + 1;
                x0 := x;
                x := x / 2.0 + 1.0 / x;
            );
            """)

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

    def test_factorial_error_flow(self):
        print(parse(self.factorial).debug(BoxState(x=1, y='1.2')))

    def test_fixpoint_error_flow(self):
        print(parse(self.fixpoint).debug(BoxState(x=[0.0, 9.0])))

    def test_newton_error_flow(self):
        print(parse(self.newton).debug(BoxState(x=[1.3, 1.4])))
