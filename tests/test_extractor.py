import unittest

from soap.datatype import int_type, FloatArrayType
from soap.expression import Variable
from soap.parser import parse
from soap.semantics.schedule.extract import ForLoopNestExtractor
from soap.semantics.state import flow_to_meta_state


def _extract_from_program(program):
    flow = parse(program)
    meta_state = flow_to_meta_state(flow)
    fix_expr = meta_state[flow.outputs[0]]
    return ForLoopNestExtractor(fix_expr)


class TestExtractor(unittest.TestCase):

    def compare(self, extractor, expect_for_loop):
        for key, expect_val in expect_for_loop.items():
            self.assertEqual(getattr(extractor, key), expect_val)

    def test_simple_loop(self):
        program = """
        #pragma soap input float a[30]
        #pragma soap output a
        for (int i = 1; i < 10; i++)
            a[i] = a[i - 1] + 1;
        """
        expect_for_loop = {
            'iter_var': Variable('i', int_type),
            'iter_slice': slice(1, 10, 1),
        }
        self.compare(_extract_from_program(program), expect_for_loop)

    def test_non_pipelineable(self):
        program = """
        #pragma soap input float a[30]
        #pragma soap output a
        for (int i = 1; i < 10; i++) {
            a[i] = a[i - 1] + 1;
            i -= 1;
        }
        """
        extractor = _extract_from_program(program)
        self.assertFalse(extractor.is_for_loop_nest)

    def test_nested_loop(self):
        program = """
        #pragma soap input float a[30]
        #pragma soap output a
        for (int i = 1; i < 10; i++)
            for (int j = 0; j < 20; j += 3)
                a[i] = a[i - j] + 1;
        """
        a = Variable('a', FloatArrayType([30]))
        i = Variable('i', int_type)
        j = Variable('j', int_type)

        extractor = _extract_from_program(program)
        expect_for_loop = {
            'iter_vars': [i, j],
            'iter_slices': [slice(1, 10, 1), slice(0, 20, 3)],
            'kernel': extractor.fix_expr.loop_state[a].loop_state,
        }
        self.compare(extractor, expect_for_loop)


class TestSandwichedNestedLoopExtractFailure(unittest.TestCase):
    pragma = '#pragma soap input float a[30]\n#pragma soap output a'

    def _test_program(self, program):
        new_program = self.pragma + program
        extractor = _extract_from_program(new_program)
        self.assertFalse(extractor.is_for_loop_nest)
        print('Expected exception:', extractor.exception)

    def test_sandwich_before(self):
        self._test_program("""
        for (int i = 1; i < 10; i++) {
            a[i] = 0;
            for (int j = 0; j < 20; j += 3)
                a[i] = a[i - j] + 1;
        }
        """)

    def test_sandwich_after(self):
        self._test_program("""
        for (int i = 1; i < 10; i++) {
            for (int j = 0; j < 20; j += 3)
                a[i] = a[i - j] + 1;
            a[i] += 1;
        }
        """)

    def test_interleave_non_pipelineable(self):
        self._test_program("""
        for (int i = 1; i < 10; i++)
            for (int j = 0; j < 20; j += 3) {
                a[i] = a[i - j] + 1;
                i = i + 1;
            }
        """)

    def test_foreign_sandwich_after(self):
        self._test_program("""
        int k = 0;
        for (int i = 1; i < 10; i++) {
            for (int j = 0; j < 20; j += 3)
                a[i] = a[i - k];
            k = i;
        }
        """)

    def test_indirect_sandwich(self):
        self._test_program("""
        int k = 0;
        int t = 0;
        for (int i = 1; i < 10; i++) {
            for (int j = 0; j < 20; j += 3)
                k++;
            a[i] = t;
            t = k;
        }
        """)
