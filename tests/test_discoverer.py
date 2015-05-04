import unittest

from soap.datatype import real_type
from soap.expression import Variable
from soap.parser import parse
from soap.semantics.state.box import BoxState
from soap.semantics.state.meta import flow_to_meta_state
from soap.semantics.functions.fixpoint import unroll_fix_expr

from soap.context import context
context.repr = 'str'


class TestUnroller(unittest.TestCase):
    def test_unroll_fix_expr(self):
        program = """
        def main() {
            real x = 0.0;
            while (x < 10) {
                x = x + 1.0;
            }
            return x;
        }
        """
        x = Variable('x', real_type)
        fix_expr = flow_to_meta_state(parse(program))[x]
        unrolled = list(unroll_fix_expr(fix_expr, BoxState(bottom=True), 2))
        self.assertEqual(fix_expr, unrolled[0])
        program = """
        def main() {
            real x = 0.0;
            while (x < 10) {
                if (x + 1.0 < 10) {
                    x = (x + 1.0) + 1.0;
                } else {
                    x = x + 1.0;
                }
            }
            return x;
        }
        """
        test_expr = flow_to_meta_state(parse(program))[x]
        self.assertEqual(test_expr, unrolled[1])

    def test_unroll_for_loop(self):
        program = """
        def main() {
            int i = 0;
            real x = 1.0;
            while (i < 9) {
                x = x * 1.1;
                i = i + 1;
            }
            return x;
        }
        """
        x = Variable('x', real_type)
        fix_expr = flow_to_meta_state(parse(program))[x]
        depth = 3
        unrolled = list(unroll_fix_expr(
            fix_expr, BoxState(bottom=True), depth))
        program = """
        def main() {
            int i = 0;
            real x = 1.0;
            while (i <= 7) {
                x = (x * 1.1) * 1.1;
                i = i + 2;
            }
            x = x * 1.1;
            return x;
        }
        """
        test_expr = flow_to_meta_state(parse(program))[x]
        self.assertEqual(test_expr, unrolled[1])


class TestDiscover(unittest.TestCase):
    pass
