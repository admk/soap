import unittest

from soap.parser import pyparse
from soap.program import generate
from soap.semantics import flow_to_meta_state

from examples import test_programs


class TestCodeGenerator(unittest.TestCase):

    def check(self, case):
        program = pyparse(case['program'])

        print('Original:')
        print(program.format())

        state = flow_to_meta_state(program)
        inputs = case['inputs']
        outputs = case['outputs']
        code = generate(state, inputs, outputs)

        print('Transformed:')
        print(code.format())

        def filter_state(state):
            return {k: v for k, v in state.items() if k in outputs}

        # input_state = case['inputs']
        # old_state = filter_state(program.flow(input_state))
        # new_state = filter_state(code.flow(input_state))
        # self.assertEqual(old_state, new_state)

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
