import unittest

from soap.expression import parse, OutputVariableTuple
from soap.program import generate, flow
from soap.semantics import BoxState, IdentifierBoxState, flow_to_meta_state
from soap.semantics.state.fusion import fusion

from examples import test_programs


class TestCodeGenerator(unittest.TestCase):

    def check(self, case):
        program = flow(case['program'])

        print('Original:')
        print(program.format())

        state = flow_to_meta_state(program)
        out_vars = case['out_vars']
        env = fusion(state.label()[1], out_vars)
        code = generate(env, out_vars)

        print('Transformed:')
        print(code.format())

        def filter_state(state):
            return {k: v for k, v in state.items() if k in out_vars}

        input_state = case['inputs']

        old_state = filter_state(program.flow(input_state))
        new_state = filter_state(code.flow(input_state))

        self.assertEqual(old_state, new_state)

        return code

    def test_if(self):
        self.check(test_programs['if'])

    def test_while(self):
        self.check(test_programs['while'])

    def test_if_fusion(self):
        self.check(test_programs['if_fusion'])

    def test_while_fusion(self):
        self.check(test_programs['while_fusion'])

    def test_nested_if(self):
        self.check(test_programs['nested_if'])

    def test_nested_while(self):
        self.check(test_programs['nested_while'])
