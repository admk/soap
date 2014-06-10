from pprint import pprint
import unittest

from akpytemp.utils import code_gobble

from soap.expression import parse, OutputVariableTuple
from soap.semantics import flow_to_meta_state
from soap.semantics.state.fusion import fusion


class TestFusion(unittest.TestCase):

    def check(self, program):
        def find_output_variable_tuple(env):
            for k, v in env.items():
                if isinstance(k, OutputVariableTuple):
                    yield k
        state = flow_to_meta_state(program)
        new_state = fusion(state.label()[1], [parse('x'), parse('y')])
        pprint(dict(new_state))
        out_vars = list(find_output_variable_tuple(new_state))
        self.assertEqual(len(out_vars), 1)
        self.assertEqual(len(out_vars.pop()), 2)

    def test_if_fusion(self):
        program = code_gobble(
            """
            if a < 1:
                x = x + 1
            if a < 1:
                y = y - 1
            """)
        self.check(program)

    def test_while_fusion(self):
        program = code_gobble(
            """
            k = x
            while x < n:
                x = x + 1
            x = k
            while x < n:
                y = y * x
                x = x + 1
            """)
        self.check(program)

    def test_if_cycle_breaking(self):
        program = code_gobble(
            """
            if a < 0:
                if b < 0:
                    x = x + 1
            if b < 0:
                if a < 0:
                    y = y - 1
            """)
        self.check(program)

    def test_nested_while(self):
        program = code_gobble(
            """
            while x < n:
                while y < x:
                    y = y + 1
                x = x + y
            """)
        self.check(program)
