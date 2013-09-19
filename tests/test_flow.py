import unittest

from soap.program import flow
from soap.semantics import ClassicalState


class TestFlow(unittest.TestCase):
    """Unittesting for :class:`soap.program.flow`."""
    def setUp(self):
        self.program = """
            while x < 10:
                y = y * x
                x = x + 1
            """.strip()
        self.flow = flow(self.program)

    def test_classical_state_flow(self):
        init_env = {
            'x': 1,
            'y': 1
        }
        final_env = dict(init_env)
        exec(self.program, final_env)
        final_env = {k: v for k, v in final_env.items() if k in init_env}
        init_state = ClassicalState(init_env)
        final_state = ClassicalState(final_env)
        self.assertEqual(self.flow.flow(init_state), final_state)

    def test_interval_flow(self):
        pass
