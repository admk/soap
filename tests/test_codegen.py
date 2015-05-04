import unittest

from soap.parser import parse
from soap.program import generate
from soap.semantics import flow_to_meta_state, BoxState

from examples import test_programs


class TestCodeGenerator(unittest.TestCase):

    def check(self, case):
        program = parse(case['program'])

        print('Original:')
        print(program.format())

        state = flow_to_meta_state(program)
        code = generate(state, BoxState(program.inputs), program.outputs)

        print('Transformed:')
        print(code.format())

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
