import unittest
import itertools
import functools

from soap.program import flow
from soap.semantics import ClassicalState, BoxState
from akpytemp.utils import code_gobble


class TestFlow(unittest.TestCase):
    """Unittesting for :class:`soap.program.flow`."""
    def setUp(self):
        self.factorial = code_gobble(
            """
            while x <= 3:
                y = y * x
                x = x + 1
            """)
        self.newton = code_gobble(
            """
            x0 = 2
            while x < x0:
                x0 = x
                x = x / 2 + 1 / x
            """)

    def exec(self, prog, cls, env):
        exec_env = dict(env)
        exec(prog, exec_env)
        return cls({k: v for k, v in exec_env.items() if k in env})

    def analyze(self, prog, cls, env):
        exec_env = self.exec(prog, cls, env)
        flow_env = flow(prog).flow(cls(env))
        return flow_env, exec_env

    def analyze_error_flow(self, prog, env):
        print()
        print(BoxState(env))
        print(flow(prog).debug(BoxState(env)))
        exec_env = self.exec(prog, BoxState, env)
        flow_env = flow(prog).flow(BoxState(env))
        self.assertLessEqual(exec_env, flow_env)

    def test_classical_state_flow(self):
        flow_env, exec_env = self.analyze(
            self.factorial, ClassicalState, {'x': 1, 'y': 1})
        self.assertEqual(flow_env, exec_env)

    def test_interval_flow(self):
        env = BoxState(x=[0, 5], y=[0, 2])
        flow_env = flow(self.factorial).flow(env)
        less_env = BoxState(x=[4, 5], y=[0, 12])
        self.assertLessEqual(less_env, flow_env)

    def test_factorial_error_flow(self):
        env = {'x': 1, 'y': float('1.2')}
        self.analyze_error_flow(self.factorial, env)

    def test_fixpoint_error_flow(self):
        env = {'x': ['1.5', '1.5']}
        self.analyze_error_flow(self.newton, env)
