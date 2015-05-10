import unittest

from soap.context import context
from soap.datatype import int_type, real_type, RealArrayType, ArrayType
from soap.expression import operators, Variable, Subscript, expression_factory
from soap.parser import parse
from soap.semantics.error import IntegerInterval, ErrorSemantics
from soap.semantics.label import Label
from soap.semantics.latency.extract import (
    ForLoopExtractor, ForLoopNestExtractor
)
from soap.semantics.latency.common import LATENCY_TABLE
from soap.semantics.latency.distance import (
    dependence_vector, dependence_distance, ISLIndependenceException
)
from soap.semantics.latency.graph import (
    SequentialLatencyDependenceGraph, LoopLatencyDependenceGraph, latency_eval
)
from soap.semantics.state import flow_to_meta_state


class TestDependenceCheck(unittest.TestCase):
    def setUp(self):
        self.x = Variable('x', dtype=int_type)
        self.y = Variable('y', dtype=int_type)
        self.sx = slice(0, 10, 1)
        self.sy = slice(1, 11, 1)

    def test_simple_subscripts(self):
        source = Subscript(
            expression_factory(operators.ADD_OP, self.x, IntegerInterval(1)))
        sink = Subscript(self.x)
        dist_vect = dependence_vector([self.x], [self.sx], source, sink)
        self.assertEqual(dist_vect, (1, ))
        dist = dependence_distance(dist_vect, [self.sx])
        self.assertEqual(dist, 1)

    def test_simple_independence(self):
        source = Subscript(
            expression_factory(operators.ADD_OP, self.x, IntegerInterval(20)))
        sink = Subscript(self.x)
        self.assertRaises(
            ISLIndependenceException, dependence_vector,
            [self.x], [self.sx], source, sink)

    def test_multi_dim_subscripts(self):
        """
        Test case::
            for (x in 0...9) {
                for (y in 1...10) {
                    a[x + 2, y] = ... a[x, y - 1] ...
                }
            }
        """
        expr = expression_factory(operators.ADD_OP, self.x, IntegerInterval(2))
        source = Subscript(expr, self.y)
        expr = expression_factory(
            operators.SUBTRACT_OP, self.y, IntegerInterval(1))
        sink = Subscript(self.x, expr)
        iter_slices = [self.sx, self.sy]
        dist_vect = dependence_vector(
            [self.x, self.y], iter_slices, source, sink)
        self.assertEqual(dist_vect, (2, 1))
        dist = dependence_distance(dist_vect, iter_slices)
        self.assertEqual(dist, 21)

    def test_multi_dim_coupled_subscripts_independence(self):
        """
        for (x in 0...9) { a[x + 1, x + 2] = a[x, x]; }
        """
        expr_1 = expression_factory(
            operators.ADD_OP, self.x, IntegerInterval(1))
        expr_2 = expression_factory(
            operators.ADD_OP, self.x, IntegerInterval(2))
        source = Subscript(expr_1, expr_2)
        sink = Subscript(self.x, self.x)
        self.assertRaises(
            ISLIndependenceException, dependence_vector,
            [self.x], [self.sx], source, sink)

    def test_multi_dim_coupled_subscripts_dependence(self):
        """
        for (x in 0...9) { a[x + 1, x + 1] = a[x, x]; }
        """
        expr_1 = expression_factory(
            operators.ADD_OP, self.x, IntegerInterval(1))
        expr_2 = expression_factory(
            operators.ADD_OP, self.x, IntegerInterval(1))
        source = Subscript(expr_1, expr_2)
        sink = Subscript(self.x, self.x)
        dist_vect = dependence_vector([self.x], [self.sx], source, sink)
        self.assertEqual(dist_vect, (1, ))


class _VariableLabelMixin(unittest.TestCase):
    def setUp(self):
        self.ori_ii_prec = context.ii_precision
        context.ii_precision = 40
        self.x = Variable('x', real_type)
        self.y = Variable('y', real_type)
        self.a = Variable('a', RealArrayType([30]))
        self.b = Variable('b', RealArrayType([30, 30]))
        self.i = Variable('i', int_type)

    def tearDown(self):
        context.ii_precision = self.ori_ii_prec


class TestSequentialLatencyDependenceGraph(_VariableLabelMixin):
    def test_simple_dag_latency(self):
        _ = tuple()
        dummy_error = ErrorSemantics(1)

        w = Variable('w', real_type)
        z = Variable('z', real_type)
        lw = Label(w, dummy_error, _)
        lx = Label(self.x, dummy_error, _)
        ly = Label(self.y, dummy_error, _)
        lz = Label(z, dummy_error, _)

        expr_1 = expression_factory(operators.MULTIPLY_OP, lw, lx)
        expr_2 = expression_factory(operators.ADD_OP, ly, lz)
        label_1 = Label(expr_1, dummy_error, _)
        label_2 = Label(expr_2, dummy_error, _)
        expr_3 = expression_factory(operators.SUBTRACT_OP, label_1, label_2)
        label_3 = Label(expr_3, dummy_error, _)

        env = {
            self.x: label_3,
            self.y: label_1,
            label_1: expr_1,
            label_2: expr_2,
            label_3: expr_3,
            lw: w,
            lx: self.x,
            ly: self.y,
            lz: z,
        }

        graph = SequentialLatencyDependenceGraph(env, [self.x, self.y])
        latency = graph.latency()
        expect_latency = LATENCY_TABLE[real_type, operators.ADD_OP]
        expect_latency += LATENCY_TABLE[real_type, operators.SUBTRACT_OP]
        self.assertEqual(latency, expect_latency)


class TestLoopLatencyDependenceGraph(_VariableLabelMixin):
    def test_variable_initiation(self):
        program = """
        def main(real x) {
            for (int i = 0; i < 9; i = i + 1) {
                x = x + 1;
            }
            return x;
        }
        """
        fix_expr = flow_to_meta_state(parse(program))[self.x]
        graph = LoopLatencyDependenceGraph(fix_expr)

        ii = graph.initiation_interval()
        expect_ii = LATENCY_TABLE[real_type, operators.ADD_OP]
        self.assertAlmostEqual(ii, expect_ii)

        trip_count = graph.trip_count()
        self.assertEqual(trip_count, 9)

        latency = graph.latency()
        expect_latency = (trip_count - 1) * ii + graph.depth()
        self.assertAlmostEqual(latency, expect_latency)

    def test_array_independence_initiation(self):
        program = """
        def main(real[30] a) {
            for (int i = 0; i < 9; i = i + 1) {
                a[i] = a[i] + 1;
            }
            return a;
        }
        """
        fix_expr = flow_to_meta_state(parse(program))[self.a]
        graph = LoopLatencyDependenceGraph(fix_expr)
        ii = graph.initiation_interval()
        expect_ii = 1
        self.assertEqual(ii, expect_ii)

    def test_simple_array_initiation(self):
        program = """
        def main(real[30] a) {
            for (int i = 0; i < 9; i = i + 1) {
                a[i] = a[i - 3] + 1;
            }
            return a;
        }
        """
        fix_expr = flow_to_meta_state(parse(program))[self.a]
        graph = LoopLatencyDependenceGraph(fix_expr)
        ii = graph.initiation_interval()
        expect_ii = LATENCY_TABLE[real_type, operators.INDEX_ACCESS_OP]
        expect_ii += LATENCY_TABLE[real_type, operators.ADD_OP]
        expect_ii += LATENCY_TABLE[ArrayType, operators.INDEX_UPDATE_OP]
        expect_ii /= 3
        self.assertAlmostEqual(ii, expect_ii)

    def test_multi_dim_array_initiation(self):
        pass

    def test_mixed_initiation(self):
        pass

    def test_full_flow(self):
        program = """
        def main(real[30] a) {
            for (int i = 0; i < 10; i = i + 1) {
                a[i + 3] = a[i] + i;
            }
            return a;
        }
        """
        meta_state = flow_to_meta_state(parse(program))
        distance = 3
        trip_count = 10
        latency = latency_eval(meta_state, [self.a])
        depth = LATENCY_TABLE[real_type, operators.INDEX_ACCESS_OP]
        depth += LATENCY_TABLE[real_type, operators.ADD_OP]
        depth += LATENCY_TABLE[ArrayType, operators.INDEX_UPDATE_OP]
        expect_ii = depth / distance
        expect_latency = expect_ii * (trip_count - 1) + depth
        self.assertAlmostEqual(latency, expect_latency)

    def test_loop_nest_flow(self):
        program = """
        def main(real[30] a) {
            int j = 0;
            while (j < 10) {
                int i = 0;
                while (i < 10) {
                    a[i + j + 3] = a[i + j] + i;
                    i = i + 1;
                }
                j = j + 1;
            }
            return a;
        }
        """
        meta_state = flow_to_meta_state(parse(program))
        latency = latency_eval(meta_state[self.a], [self.a])
        distance = 3
        trip_count = 10 * 10
        depth = LATENCY_TABLE[real_type, operators.INDEX_ACCESS_OP]
        depth += LATENCY_TABLE[real_type, operators.ADD_OP]
        depth += LATENCY_TABLE[ArrayType, operators.INDEX_UPDATE_OP]
        expect_ii = depth / distance
        add_latency = LATENCY_TABLE[int_type, operators.ADD_OP]
        expect_latency = expect_ii * (trip_count - 1) + depth + add_latency
        self.assertAlmostEqual(latency, expect_latency)

    def test_multi_dim_flow(self):
        program = """
        def main(real[30, 30] b, int j) {
            for (int i = 0; i < 10; i = i + 1) {
                b[i + 3, j] = (b[i, j] + i) + j;
            }
            return b;
        }
        """
        meta_state = flow_to_meta_state(parse(program))
        latency = latency_eval(meta_state[self.b], [self.b])
        distance = 3
        trip_count = 10
        depth = LATENCY_TABLE[real_type, operators.INDEX_ACCESS_OP]
        depth += LATENCY_TABLE[real_type, operators.ADD_OP]
        depth += LATENCY_TABLE[real_type, operators.ADD_OP]
        depth += LATENCY_TABLE[ArrayType, operators.INDEX_UPDATE_OP]
        expect_ii = depth / distance
        expect_latency = expect_ii * (trip_count - 1) + depth
        self.assertAlmostEqual(latency, expect_latency)


class TestExtraction(_VariableLabelMixin):
    def compare(self, for_loop, expect_for_loop):
        for key, expect_val in expect_for_loop.items():
            self.assertEqual(getattr(for_loop, key), expect_val)

    def test_simple_loop(self):
        program = """
        def main(real[30] a) {
            for (int i = 1; i < 10; i = i + 1) {
                a[i] = a[i - 1] + 1;
            }
            return a;
        }
        """
        flow = parse(program)
        meta_state = flow_to_meta_state(flow)
        fix_expr = meta_state[flow.outputs[0]]
        for_loop = ForLoopExtractor(fix_expr)
        expect_for_loop = {
            'iter_var': self.i,
            'start': IntegerInterval(1),
            'stop': IntegerInterval(10),
            'step': IntegerInterval(1),
            'has_inner_loops': False,
        }
        self.compare(for_loop, expect_for_loop)

    def test_nested_loop(self):
        program = """
        def main(real[30] a) {
            for (int i = 1; i < 10; i = i + 1) {
                for (int j = 0; j < 20; j = j + 3) {
                    a[i] = a[i - j] + 1;
                }
            }
            return a;
        }
        """
        flow = parse(program)
        meta_state = flow_to_meta_state(flow)

        a = flow.outputs[0]
        i = Variable('i', int_type)
        j = Variable('j', int_type)

        fix_expr = meta_state[a]
        for_loop = ForLoopNestExtractor(fix_expr)
        expect_for_loop = {
            'iter_vars': [i, j],
            'iter_slices': [slice(1, 10, 1), slice(0, 20, 3)],
            'kernel': fix_expr.loop_state[a].loop_state,
        }
        self.compare(for_loop, expect_for_loop)
