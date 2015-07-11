import nose
import unittest

from soap.analysis.core import Analysis
from soap.context import context
from soap.expression import Expression, operators
from soap.parser import expr_parse, parse
from soap.semantics import BoxState, flow_to_meta_state, label
from soap.transformer import arithmetic, pattern
from soap.transformer.partition import partition_optimize
from soap.transformer.utils import parsings, reduce
from soap.transformer.linalg import linear_algebra_simplify


Expression.__repr__ = lambda self: self.__str__()


class TestArithmeticEquivalence(unittest.TestCase):
    """
    Unit testing for :mod:`soap.transformer.arithmetic`.
    """
    def test_associativity(self):
        for e in ['(a + b) + c', '(b + a) + c', 'c + (a + b)', 'c + (b + a)']:
            f = pattern.transform(
                arithmetic.associativity_addition, expr_parse(e))
            self.assertIn(expr_parse('a + (b + c)'), f)
            self.assertIn(expr_parse('b + (a + c)'), f)
        for e in ['(a * b) * c', '(b * a) * c', 'c * (a * b)', 'c * (b * a)']:
            f = pattern.transform(
                arithmetic.associativity_multiplication, expr_parse(e))
            self.assertIn(expr_parse('a * (b * c)'), f)
            self.assertIn(expr_parse('b * (a * c)'), f)

    def test_distributivity_distribute(self):
        for e in ['(a + b) * c', '(b + a) * c', 'c * (a + b)', 'c * (b + a)']:
            f = pattern.transform(
                arithmetic.distributivity_distribute_multiplication,
                expr_parse(e))
            self.assertIn(expr_parse('a * c + b * c'), f)
        e = expr_parse('-(a + b)')
        f = pattern.transform(
            arithmetic.distributivity_distribute_unary_subtraction_addition, e)
        self.assertIn(expr_parse('-a - b'), f)

    def test_distributivity_collect(self):
        e = expr_parse('c * a + b * c')
        f = pattern.transform(
            arithmetic.distributivity_collect_multiplication, e)
        self.assertIn(expr_parse('(a + b) * c'), f)

    def test_negation(self):
        e = expr_parse('a - b')
        f = pattern.transform(arithmetic.negation_1, e)
        self.assertIn(expr_parse('a + -b'), f)

    def test_identity_reduction(self):
        e = expr_parse('0 + a')
        f = pattern.transform(arithmetic.identity_reduction_addition, e)
        self.assertIn(expr_parse('a'), f)
        e = expr_parse('1 * a')
        f = pattern.transform(arithmetic.identity_reduction_multiplication, e)
        self.assertIn(expr_parse('a'), f)
        e = expr_parse('a / 1')
        f = pattern.transform(arithmetic.identity_reduction_division, e)
        self.assertIn(expr_parse('a'), f)

    def test_double_negation_reduction(self):
        e = expr_parse('--a')
        f = pattern.transform(arithmetic.double_negation_reduction, e)
        self.assertIn(expr_parse('a'), f)

    def test_zero_reduction(self):
        e = expr_parse('a * 0')
        f = pattern.transform(arithmetic.zero_reduction_multiplication, e)
        self.assertIn(expr_parse('0'), f)
        e = expr_parse('0 / a')
        f = pattern.transform(arithmetic.zero_reduction_division, e)
        self.assertIn(expr_parse('0'), f)

    def test_constant_reduction(self):
        e = expr_parse('1 + 2')
        f = pattern.transform(arithmetic.constant_reduction, e)
        self.assertIn(expr_parse('3'), f)


class TestArithTreeTransformer(unittest.TestCase):
    """
    Unit testing for :class:`soap.transformer.arithmetic.ArithTreeTransformer`.
    """
    def test_parsings(self):
        e = expr_parse('a + b + c + d')
        f = parsings(e)
        g = {
            expr_parse('((a + b) + c) + d'),
            expr_parse('(a + (b + c)) + d'),
            expr_parse('(a + (b + d)) + c'),
            expr_parse('(a + b) + (c + d)'),
            expr_parse('(a + c) + (b + d)'),
            expr_parse('(b + (a + c)) + d'),
            expr_parse('(b + (a + d)) + c'),
            expr_parse('(b + c) + (a + d)'),
            expr_parse('a + ((b + c) + d)'),
            expr_parse('a + (b + (c + d))'),
            expr_parse('a + (c + (b + d))'),
            expr_parse('b + ((a + c) + d)'),
            expr_parse('b + ((a + d) + c)'),
            expr_parse('b + (a + (c + d))'),
            expr_parse('c + ((a + b) + d)'),
        }
        self.assertEqual(f, g)

    def test_reduction(self):
        e = {
            expr_parse('a + 1 * b'),
            expr_parse('a * 1 + b'),
            expr_parse('(a + 0) + b'),
        }
        f = reduce(e)
        g = {
            expr_parse('a + b')
        }
        self.assertEqual(f, g)


class TestLinearAlgebraSimplifier(unittest.TestCase):
    def test_simple(self):
        flow = parse(
            """
            #pragma soap input float a[20], int i
            #pragma soap output r, s, t, a
            float r = a[i + 1];
            a[i - 1] = 3;
            float s = a[i - 2 + 1];
            float t = a[i + 1];
            a[i - 1] = 4;
            """)
        meta_state = linear_algebra_simplify(flow_to_meta_state(flow))
        r_expr, s_expr, t_expr, a_expr = (
            meta_state[flow.outputs[i]] for i in range(4))
        self.assertEqual(s_expr, expr_parse('3'))
        self.assertEqual(t_expr, r_expr)
        self.assertEqual(a_expr.var.name, 'a')

    def _count(self, env, op):
        count = 0
        for e in env.values():
            try:
                if e.op == op:
                    count += 1
            except AttributeError:
                pass
        return count

    def test_full(self):
        flow = parse(
            """
            #pragma soap input float a[20] = [0.0, 1.0]
            #pragma soap output a
            for (int i = 3; i < 21; i = i + 2) {
                a[i] = (a[i - 1] + a[i - 2] + a[i - 3]) / 3;
                int j = i + 1;
                a[j] = (a[j - 1] + a[j - 2] + a[j - 3]) / 3;
            }
            """)
        expr = flow_to_meta_state(flow)[flow.outputs[0]]
        expr = linear_algebra_simplify(expr)
        print(expr.format())
        env = label(expr.loop_state, None, None)[1]
        access_count = self._count(env, operators.INDEX_ACCESS_OP)
        update_count = self._count(env, operators.INDEX_UPDATE_OP)
        self.assertEqual(access_count, 3)
        self.assertEqual(update_count, 2)


class TestPartition(unittest.TestCase):
    def setUp(self):
        context.take_snapshot()
        context.unroll_depth = 0

    def tearDown(self):
        context.restore_snapshot()

    def program(self, iteration_count):
        flow = parse(
            """
            #pragma soap input float a[200][200] = [0.0, 1.0], int i=[0, 100]
            #pragma soap output a
            for (int j = 1; j < {}; j++)
                a[i][j] = 0.2 * (
                    a[i][j-1] + a[i][j] + a[i][j+1] + a[i+1][j] + a[i-1][j]);
            """.format(iteration_count))
        meta_state = flow_to_meta_state(flow)
        return meta_state, BoxState(flow.inputs), flow.outputs

    def test_generate(self):
        alg = lambda expr, state, _: {expr}
        meta_state, state, outputs = self.program(10)
        results = partition_optimize(
            meta_state, state, outputs, optimize_algorithm=alg)

        self.assertEqual(len(results), 1)
        result = results.pop()
        compare_meta_state = result.expression
        self.assertEqual(
            meta_state[outputs[0]], compare_meta_state[outputs[0]])

    def test_optimize(self):
        raise nose.SkipTest
        meta_state, state, outputs = self.program(100)
        with context.local(unroll_depth=1):
            env_set = partition_optimize(meta_state, state, outputs)
        analysis = Analysis(
            {self.meta_state}, self.state, [self.output], round_values=True)
        print('Original: ', analysis.analyze().pop().format())
        self.assertGreater(len(env_set), 1)
