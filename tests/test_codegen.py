import unittest

from soap.parser import parse
from soap.program import generate
from soap.semantics import flow_to_meta_state

from examples import test_programs


class TestCodeGenerator(unittest.TestCase):

    def check(self, program):
        program = parse(program)

        print('Original:')
        print(program.format())

        state = flow_to_meta_state(program)
        code = generate(state, program.inputs, program.outputs)

        print('Transformed:')
        print(code.format())

    def check_case(self, case):
        return self.check(case['program'])

    def test_if(self):
        self.check_case(test_programs['if'])

    def test_while(self):
        self.check_case(test_programs['while'])

    def test_if_fusion(self):
        self.check_case(test_programs['if_fusion'])

    def test_while_fusion(self):
        self.check_case(test_programs['while_fusion'])

    def test_nested_if(self):
        self.check_case(test_programs['nested_if'])

    def test_nested_while(self):
        self.check_case(test_programs['nested_while'])

    def test_datatypes(self):
        program = """
        #pragma soap input float x=10, int y=20, int z=30
        #pragma soap output w
        float w = (x * y) + (y * z) + (x * z);
        """
        self.check(program)

    def test_simple_access(self):
        program = """
        #pragma soap input float x[30]=3, int y=4
        #pragma soap output z
        float z = x[y];
        """
        self.check(program)

    def test_simple_update(self):
        program = """
        #pragma soap input float x[30]=3, int y=4
        #pragma soap output x
        x[y + 1] = y + 2;
        """
        self.check(program)

    def test_linalg_order(self):
        program = """
        #pragma soap input float x[30]=3, int y=4
        #pragma soap output x, z
        float z = x[y];
        x[y] = y + 2;
        """
        self.check(program)

    def test_linalg_flow(self):
        program = """
        #pragma soap input float x[30]=3, int y=4
        #pragma soap output x
        for (int i = 0; i < 10; i++) {
            x[i] = x[i - 1] + y;
        }
        """
        self.check(program)
