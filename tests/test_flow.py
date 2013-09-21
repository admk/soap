import unittest

from soap.program import flow
from soap.semantics import ClassicalState, IntervalState


class TestFlow(unittest.TestCase):
    """Unittesting for :class:`soap.program.flow`."""
    def setUp(self):
        self.factorial = """
            while x <= 3:
                y = y * x
                x = x + 1
            """.strip()

    def analyze(self, prog, cls, env):
        state = cls(env)
        final_env = dict(env)
        exec(prog, final_env)
        final_env = {k: v for k, v in final_env.items() if k in env}
        final_state = cls(final_env)
        self.assertEqual(flow(prog).flow(state), final_state)

    def test_classical_state_flow(self):
        self.analyze(self.factorial, ClassicalState, {'x': 1, 'y': 1})

    def test_interval_flow(self):
        self.analyze(self.factorial, IntervalState, {'x': 1, 'y': 1})
