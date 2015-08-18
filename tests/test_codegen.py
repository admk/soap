import unittest

from soap.context import context
from soap.parser import parse
from soap.program import generate
from soap.semantics import flow_to_meta_state, arith_eval, BoxState

from examples import test_programs


class TestCodeGenerator(unittest.TestCase):
    def setUp(self):
        context.take_snapshot()
        context.fast_outer = False
        context.fast_factor = 1
        context.scalar_array = False

    def tearDown(self):
        context.restore_snapshot()

    def check(self, program):
        program = parse(program)
        inputs = BoxState(program.inputs)

        print('Original:')
        print(program.format())

        state = flow_to_meta_state(program)
        result = arith_eval(state.filter(program.outputs), inputs)
        code = generate(state, program.inputs, program.outputs)

        code_str = code.format()
        print('Transformed:')
        print(code_str)

        gen_flow = parse(code_str)
        gen_state = flow_to_meta_state(gen_flow).filter(program.outputs)
        compare_result = arith_eval(gen_state, inputs)

        self.assertEqual(result, compare_result)

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

    def test_linalg_if(self):
        program = """
        #pragma soap input float x[30]=3, int y=4
        #pragma soap output x
        if (y > 1)
            x[y] = x[y - 1] + 1;
        """
        self.check(program)

    def test_linalg_for(self):
        program = """
        #pragma soap input float x[30]=3, int y=4
        #pragma soap output x
        for (int i = 1; i < 10; i++) {
            x[i] = x[i - 1] + y;
        }
        """
        self.check(program)
