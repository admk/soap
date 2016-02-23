import unittest

from soap.context import context
from soap.datatype import (
    auto_type, int_type, float_type, FloatArrayType, ArrayType
)
from soap.expression import (
    operators, Variable, Subscript, expression_factory
)
from soap.parser import parse
from soap.semantics.error import IntegerInterval
from soap.semantics.functions.label import label
from soap.semantics.label import Label
from soap.semantics.schedule.distance import (
    dependence_vector, dependence_distance, ISLIndependenceException
)
from soap.semantics.schedule.common import schedule_graph
from soap.semantics.schedule.graph import (
    LoopScheduleGraph, SequentialScheduleGraph
)
from soap.semantics.schedule.table import LATENCY_TABLE
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
        # for (x in 0...9) for (y in 1...10) a[x + 2, y] = ... a[x, y - 1] ...
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
        # for (x in 0...9) { a[x + 1, x + 2] = a[x, x]; }
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
        # for (x in 0...9) { a[x + 1, x + 1] = a[x, x]; }
        expr_1 = expression_factory(
            operators.ADD_OP, self.x, IntegerInterval(1))
        expr_2 = expression_factory(
            operators.ADD_OP, self.x, IntegerInterval(1))
        source = Subscript(expr_1, expr_2)
        sink = Subscript(self.x, self.x)
        dist_vect = dependence_vector([self.x], [self.sx], source, sink)
        self.assertEqual(dist_vect, (1, ))


class _CommonMixin(unittest.TestCase):
    def setUp(self):
        context.take_snapshot()
        context.ii_precision = 30
        context.round_values = False
        context.scheduler = 'alap'
        self.x = Variable('x', float_type)
        self.y = Variable('y', float_type)
        self.a = Variable('a', FloatArrayType([30]))
        self.b = Variable('b', FloatArrayType([30, 30]))
        self.c = Variable('c', FloatArrayType([30]))
        self.i = Variable('i', int_type)

    def tearDown(self):
        context.restore_snapshot()


class TestLoopScheduleGraph(_CommonMixin):
    def test_variable_initiation(self):
        program = """
        #pragma soap input float x
        #pragma soap output x
        for (int i = 0; i < 9; i = i + 1) {
            x = x + 1;
        }
        """
        fix_expr = flow_to_meta_state(parse(program))[self.x]
        graph = LoopScheduleGraph(fix_expr)

        ii = graph.initiation_interval()
        expect_ii = LATENCY_TABLE[float_type][operators.ADD_OP]
        self.assertAlmostEqual(ii, expect_ii)

        trip_count = graph.trip_count()
        self.assertEqual(trip_count, 9)

        latency = graph.latency()
        expect_latency = (trip_count - 1) * ii + graph.depth()
        self.assertAlmostEqual(latency, expect_latency)

    def test_array_independence_initiation(self):
        program = """
        #pragma soap input float a[30]
        #pragma soap output a
        for (int i = 0; i < 9; i = i + 1)
            a[i] = a[i] + 1;
        """
        fix_expr = flow_to_meta_state(parse(program))[self.a]
        graph = LoopScheduleGraph(fix_expr)
        ii = graph.initiation_interval()
        expect_ii = 1
        self.assertEqual(ii, expect_ii)

    def test_simple_array_initiation(self):
        program = """
        #pragma soap input float a[30]
        #pragma soap output a
        for (int i = 0; i < 9; i = i + 1)
            a[i] = a[i - 3] + 1;
        """
        fix_expr = flow_to_meta_state(parse(program))[self.a]
        graph = LoopScheduleGraph(fix_expr)
        ii = graph.initiation_interval()
        expect_ii = LATENCY_TABLE[float_type][operators.INDEX_ACCESS_OP]
        expect_ii += LATENCY_TABLE[float_type][operators.ADD_OP]
        expect_ii += LATENCY_TABLE[ArrayType][operators.INDEX_UPDATE_OP]
        expect_ii /= 3
        self.assertAlmostEqual(ii, expect_ii)

    def test_simple_array_unroll_initiation(self):
        program = """
        #pragma soap input float a[30]
        #pragma soap output a
        for (int i = 0; i < 10; i = i + 1)
            a[i] = a[i - 1] + 1.0;
        """
        unroll_program = """
        #pragma soap input float a[30]
        #pragma soap output a
        for (int i = 0; i < 9; i = i + 2) {
            a[i] = a[i - 1] + 1.0;
            a[i + 1] = a[i] + 1.0;
        }
        """
        fix_expr = flow_to_meta_state(parse(program))[self.a]
        graph = LoopScheduleGraph(fix_expr)
        ii = graph.initiation_interval()

        unroll_fix_expr = flow_to_meta_state(parse(unroll_program))[self.a]
        unroll_graph = LoopScheduleGraph(unroll_fix_expr)
        unroll_ii = unroll_graph.initiation_interval()

        expect_ii = LATENCY_TABLE[float_type][operators.INDEX_ACCESS_OP]
        expect_ii += LATENCY_TABLE[float_type][operators.ADD_OP]
        expect_ii += LATENCY_TABLE[ArrayType][operators.INDEX_UPDATE_OP]

        self.assertAlmostEqual(ii, expect_ii)
        self.assertAlmostEqual(unroll_ii, 2 * expect_ii)

    def test_transitive_initiation(self):
        program = """
        #pragma soap output y
        float x = 1.0;
        float x0 = x;
        float y = 1.0;
        for (int i = 0; i < 9; i = i + 1) {
            x0 = x;
            x = y + 1.0;
            y = x0 * 2.0;
        }
        """
        fix_expr = flow_to_meta_state(parse(program))[self.y]
        graph = LoopScheduleGraph(fix_expr)
        ii = graph.initiation_interval()
        expect_ii = LATENCY_TABLE[float_type][operators.ADD_OP]
        expect_ii += LATENCY_TABLE[float_type][operators.MULTIPLY_OP]
        expect_ii /= 2
        self.assertAlmostEqual(ii, expect_ii)

    def test_mixed_array_transitive_initiation(self):
        program = """
        #pragma soap input float a[30], float c[30]
        #pragma soap output a
        for (int i = 0; i < 9; i = i + 1) {
            a[i] = c[i - 1] + 1.0;
            c[i] = a[i - 1] * 2.0;
        }
        """
        fix_expr = flow_to_meta_state(parse(program))[self.a]
        graph = LoopScheduleGraph(fix_expr)
        ii = graph.initiation_interval()
        expect_ii = LATENCY_TABLE[float_type][operators.INDEX_ACCESS_OP]
        expect_ii += LATENCY_TABLE[float_type][operators.ADD_OP]
        expect_ii += LATENCY_TABLE[ArrayType][operators.INDEX_UPDATE_OP]
        expect_ii += LATENCY_TABLE[float_type][operators.INDEX_ACCESS_OP]
        expect_ii += LATENCY_TABLE[float_type][operators.MULTIPLY_OP]
        expect_ii += LATENCY_TABLE[ArrayType][operators.INDEX_UPDATE_OP]
        expect_ii /= 2
        self.assertAlmostEqual(ii, expect_ii)

    def test_recurrence_info(self):
        program = """
        #pragma soap input float a[30]
        #pragma soap output a
        for (int i = 0; i < 30; i = i + 1)
            a[i] = a[i - 3] * 2;
        """
        flow = parse(program)
        meta_state = flow_to_meta_state(flow)
        fix_expr = meta_state[flow.outputs[0]]
        graph = LoopScheduleGraph(fix_expr)
        im1 = expression_factory(
            operators.SUBTRACT_OP, self.i, IntegerInterval(3))
        access = expression_factory(
            operators.INDEX_ACCESS_OP, self.a, Subscript(im1))
        update = expression_factory(
            operators.INDEX_UPDATE_OP, self.a, Subscript(self.i),
            Variable('__dont_care', auto_type))
        compare_set = {
            (self.i, self.i, 1),
            (access, update, 3),
        }
        self.assertSetEqual(graph.recurrences, compare_set)


class TestSequentialScheduleGraph(_CommonMixin):
    def _to_graph(self, program):
        flow = parse(program)
        meta_state = flow_to_meta_state(flow)
        outputs = flow.outputs
        lab, env = label(meta_state, None, outputs)
        return SequentialScheduleGraph(env, outputs)

    def _simple_dag(self):
        program = """
        #pragma soap input float w, float x, int y, int z
        #pragma soap output x
        x = (w + x) * (y + z) - (w + z);
        """
        return self._to_graph(program)

    def test_simple_dag_latency(self):
        graph = self._simple_dag()
        expect_latency = LATENCY_TABLE[float_type][operators.ADD_OP]
        expect_latency += LATENCY_TABLE[float_type][operators.MULTIPLY_OP]
        expect_latency += LATENCY_TABLE[float_type][operators.SUBTRACT_OP]
        self.assertEqual(graph.latency(), expect_latency)

    def test_simple_dag_resource(self):
        graph = self._simple_dag()
        total_map, min_alloc_map = graph.resource()
        compare_total_map = {
            (int_type, operators.ADD_OP): 1,
            (float_type, operators.ADD_OP): 3,
            (float_type, operators.MULTIPLY_OP): 1,
        }
        compare_min_alloc_map = {
            (int_type, operators.ADD_OP): 1,
            (float_type, operators.ADD_OP): 1,
            (float_type, operators.MULTIPLY_OP): 1,
        }
        self.assertEqual(total_map, compare_total_map)
        self.assertEqual(min_alloc_map, compare_min_alloc_map)

    def test_simple_recurrence_aware_latency(self):
        program = """
        #pragma soap input float x, int y, float z
        #pragma soap output x
        x = z * z * z * z * z * z * z * z * z * z * z * z * z + (x * y + x);
        """
        graph = self._to_graph(program)
        graph.recurrences = [(self.x, self.x, 1)]
        expect_latency = LATENCY_TABLE[float_type][operators.MULTIPLY_OP]
        expect_latency += LATENCY_TABLE[float_type][operators.ADD_OP]
        expect_latency += LATENCY_TABLE[float_type][operators.ADD_OP]
        self.assertEqual(graph.latency(), expect_latency)

    def test_array_recurrence_aware_latency(self):
        program = """
        #pragma soap input float a[30], int i
        #pragma soap output a
        a[i] = (a[i - 1] + (a[i - 2] + a[i - 3])) / 3;
        """
        graph = self._to_graph(program)
        im1 = expression_factory(
            operators.SUBTRACT_OP, self.i, IntegerInterval(1))
        access = expression_factory(
            operators.INDEX_ACCESS_OP, self.a, Subscript(im1))
        update = expression_factory(
            operators.INDEX_UPDATE_OP, self.a, Subscript(self.i), None)
        graph.recurrences = [(access, update, 1)]
        expect_latency = LATENCY_TABLE[float_type][operators.INDEX_ACCESS_OP]
        expect_latency += LATENCY_TABLE[float_type][operators.ADD_OP]
        expect_latency += LATENCY_TABLE[float_type][operators.DIVIDE_OP]
        expect_latency += LATENCY_TABLE[ArrayType][operators.INDEX_UPDATE_OP]
        self.assertEqual(graph.latency(), expect_latency)

    def test_loop_sequentialization(self):
        program = """
        #pragma soap input float x[30], float y[30]
        #pragma soap output z
        for (int i = 1; i < 30; i = i + 1)
            x[i] = x[i - 1] + 1;
        for (int j = 1; j < 20; j = j + 1)
            y[j] = y[j - 1] + 1;
        float z = x[0] + y[0];
        """
        loop_ii = LATENCY_TABLE[float_type][operators.INDEX_ACCESS_OP]
        loop_ii += LATENCY_TABLE[float_type][operators.ADD_OP]
        loop_ii += LATENCY_TABLE[ArrayType][operators.INDEX_UPDATE_OP]
        loop_depth = loop_ii
        loop_depth += LATENCY_TABLE[int_type][operators.SUBTRACT_OP]
        trip_count_i = 29
        trip_count_j = 19
        seq_loop_latency = (trip_count_i + trip_count_j - 2) * loop_ii
        seq_loop_latency += loop_depth * 2
        seq_latency = seq_loop_latency
        seq_latency += LATENCY_TABLE[float_type][operators.INDEX_ACCESS_OP]
        seq_latency += LATENCY_TABLE[float_type][operators.ADD_OP]

        graph = self._to_graph(program)
        graph.sequentialize_loops = True
        self.assertAlmostEqual(graph.latency(), seq_latency, delta=2)

        par_loop_latency = (max(trip_count_i, trip_count_j) - 1) * loop_ii
        par_loop_latency += loop_depth
        par_latency = par_loop_latency
        par_latency += LATENCY_TABLE[float_type][operators.INDEX_ACCESS_OP]
        par_latency += LATENCY_TABLE[float_type][operators.ADD_OP]

        graph = self._to_graph(program)
        graph.sequentialize_loops = False
        self.assertAlmostEqual(graph.latency(), par_latency, delta=2)


class TestFullSchedule(_CommonMixin):
    def assertStatisticsAlmostEqual(
            self, graph, expect_latency, expect_resource, delta=1):
        latency = graph.latency()
        self.assertAlmostEqual(latency, expect_latency, delta=delta)
        total_resource, resource = graph.resource()
        self.assertTrue(set(expect_resource) <= set(resource))
        for dtype_op, expect_count in expect_resource.items():
            count = resource[dtype_op]
            try:
                self.assertAlmostEqual(count, expect_count, delta=0.01)
            except AssertionError:
                raise AssertionError(
                    'Resource count mismatch for operator {}: {} != {}'
                    .format(dtype_op, count, expect_count))

    def test_simple_flow(self):
        program = """
        #pragma soap input float a[30]
        #pragma soap output a
        for (int i = 0; i < 10; i = i + 1)
            a[i + 3] = a[i] + i;
        """
        meta_state = flow_to_meta_state(parse(program))
        distance = 3
        trip_count = 10
        graph = schedule_graph(meta_state, [self.a])
        depth = LATENCY_TABLE[float_type][operators.INDEX_ACCESS_OP]
        depth += LATENCY_TABLE[float_type][operators.ADD_OP]
        depth += LATENCY_TABLE[ArrayType][operators.INDEX_UPDATE_OP]
        expect_ii = depth / distance
        expect_latency = expect_ii * (trip_count - 1) + depth
        expect_resource = {
            (int_type, operators.ADD_OP): 2 / expect_ii,
            (float_type, operators.ADD_OP): 1 / expect_ii,
        }
        self.assertStatisticsAlmostEqual(
            graph, expect_latency, expect_resource)

    def test_loop_nest_flow(self):
        program = """
        #pragma soap input float a[30]
        #pragma soap output a
        int j = 0;
        while (j < 10) {
            int i = 0;
            while (i < 10) {
                a[i + j + 3] = a[i + j] + i;
                i = i + 1;
            }
            j = j + 1;
        }
        """
        meta_state = flow_to_meta_state(parse(program))
        graph = schedule_graph(meta_state[self.a], [self.a])
        distance = 3
        trip_count = 10 * 10
        depth = LATENCY_TABLE[float_type][operators.INDEX_ACCESS_OP]
        depth += LATENCY_TABLE[float_type][operators.ADD_OP]
        depth += LATENCY_TABLE[ArrayType][operators.INDEX_UPDATE_OP]
        expect_ii = depth / distance
        add_latency = LATENCY_TABLE[int_type][operators.ADD_OP]
        expect_latency = expect_ii * (trip_count - 1) + depth + add_latency
        expect_resource = {
            (int_type, operators.ADD_OP): 3 / expect_ii,
            (float_type, operators.ADD_OP): 1 / expect_ii,
        }
        self.assertStatisticsAlmostEqual(
            graph, expect_latency, expect_resource)

    def test_multi_dim_flow(self):
        program = """
        #pragma soap input float b[30][30], int j
        #pragma soap output b
        for (int i = 0; i < 10; i = i + 1)
            b[i + 3][j] = (b[i][j] + i) + j;
        """
        meta_state = flow_to_meta_state(parse(program))
        graph = schedule_graph(meta_state[self.b], [self.b])
        distance = 3
        trip_count = 10
        depth = LATENCY_TABLE[float_type][operators.INDEX_ACCESS_OP]
        depth += LATENCY_TABLE[float_type][operators.ADD_OP]
        depth += LATENCY_TABLE[float_type][operators.ADD_OP]
        depth += LATENCY_TABLE[ArrayType][operators.INDEX_UPDATE_OP]
        expect_ii = depth / distance
        expect_latency = expect_ii * (trip_count - 1) + depth
        expect_resource = {
            (int_type, operators.ADD_OP): 2 / expect_ii,
            (float_type, operators.ADD_OP): 2 / expect_ii,
        }
        self.assertStatisticsAlmostEqual(
            graph, expect_latency, expect_resource)

    def test_resource_constraint_on_ii(self):
        program = """
        #pragma soap input float a[30]
        #pragma soap output a
        for (int i = 0; i < 10; i = i + 1)
            a[i] = a[i] + a[i + 1] + a[i + 2] + a[i + 3];
        """
        meta_state = flow_to_meta_state(parse(program))
        graph = schedule_graph(meta_state[self.a], [self.a])
        trip_count = 10
        depth = LATENCY_TABLE[int_type][operators.ADD_OP]
        depth += LATENCY_TABLE[float_type][operators.INDEX_ACCESS_OP]
        depth += LATENCY_TABLE[float_type][operators.ADD_OP]
        depth += LATENCY_TABLE[float_type][operators.ADD_OP]
        depth += LATENCY_TABLE[float_type][operators.ADD_OP]
        depth += LATENCY_TABLE[ArrayType][operators.INDEX_UPDATE_OP]
        expect_ii = 5 / 2
        expect_latency = (trip_count - 1) * expect_ii + depth
        expect_resource = {
            (int_type, operators.ADD_OP): 3 / expect_ii,
            (float_type, operators.ADD_OP): 3 / expect_ii,
        }
        self.assertStatisticsAlmostEqual(
            graph, expect_latency, expect_resource)

    def test_sequence_of_loops(self):
        program = """
        #pragma soap input float a[30]
        #pragma soap output a
        for (int i = 0; i < 10; i = i + 1)
            a[i] = a[i - 1] + i;
        for (int j = 0; j < 20; j = j + 1)
            a[j] = a[j - 2] + a[j];
        """
        meta_state = flow_to_meta_state(parse(program))
        graph = schedule_graph(meta_state[self.a], [self.a])
        kernel_lat = LATENCY_TABLE[float_type][operators.INDEX_ACCESS_OP]
        kernel_lat += LATENCY_TABLE[float_type][operators.ADD_OP]
        kernel_lat += LATENCY_TABLE[ArrayType][operators.INDEX_UPDATE_OP]
        depth_1 = LATENCY_TABLE[int_type][operators.ADD_OP] + kernel_lat
        depth_2 = max(
            LATENCY_TABLE[int_type][operators.ADD_OP],
            LATENCY_TABLE[float_type][operators.INDEX_ACCESS_OP])
        depth_2 += kernel_lat
        ii_1 = kernel_lat
        ii_2 = kernel_lat / 2
        trip_count_1 = 10
        trip_count_2 = 20
        latency_1 = (trip_count_1 - 1) * ii_1 + depth_1
        latency_2 = (trip_count_2 - 1) * ii_2 + depth_2
        expect_latency = latency_1 + latency_2
        expect_resource = {
            (int_type, operators.ADD_OP): 2 / kernel_lat,
            (float_type, operators.ADD_OP): 2 / kernel_lat,
        }
        self.assertStatisticsAlmostEqual(
            graph, expect_latency, expect_resource, delta=2)

    def test_non_pipelineable(self):
        program = """
        #pragma soap input float a[30], int j
        #pragma soap output a
        for (int i = 0; i < 10; i = i + j)
            a[i + 3] = a[i] + i;
        """
        meta_state = flow_to_meta_state(parse(program))
        graph = schedule_graph(meta_state, [self.a])
        expect_latency = float('inf')
        expect_resource = {
            (int_type, operators.ADD_OP): 1,
            (float_type, operators.ADD_OP): 1,
        }
        self.assertStatisticsAlmostEqual(
            graph, expect_latency, expect_resource)
