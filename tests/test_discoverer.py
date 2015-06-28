import unittest

from soap.datatype import real_type
from soap.expression import Variable
from soap.parser import parse
from soap.semantics.state.box import BoxState
from soap.semantics.state.meta import flow_to_meta_state
from soap.semantics.functions.arithmetic import arith_eval
from soap.semantics.functions.fixpoint import unroll_fix_expr


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
        unrolled = list(unroll_fix_expr(fix_expr, 2))
        for u in unrolled: print(u.format())
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
            real x = 1.0;
            for (int i = 0; i < 9; i = i + 1) {
                x = x + 2.0;
            }
            return x;
        }
        """
        x = Variable('x', real_type)
        fix_expr = flow_to_meta_state(parse(program))[x]
        depth = 3
        unrolled = list(unroll_fix_expr(fix_expr, depth))
        program = """
        def main() {
            real x = 1.0;
            for (int i = 0; i < 8; i = i + 2) {
                x = (x + 2.0) + 2.0;
            }
            x = x + 2.0;
            return x;
        }
        """
        test_expr = flow_to_meta_state(parse(program))[x]
        self.assertEqual(test_expr, unrolled[1])
        inputs = BoxState(bottom=True)
        for unrolled_expr in unrolled:
            self.assertEqual(
                arith_eval(fix_expr, inputs),
                arith_eval(unrolled_expr, inputs))


class TestDiscoverer(unittest.TestCase):
    pass
