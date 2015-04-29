import unittest

from soap.context import context
from soap.datatype import (
    int_type, real_type, RealArrayType, ArrayType
)
from soap.expression import (
    operators, Variable, Subscript, expression_factory, FixExpr, BinaryBoolExpr
)
from soap.parser import parse
from soap.semantics.error import IntegerInterval, ErrorSemantics
from soap.semantics.label import Label, LabelSemantics
from soap.semantics.latency.extract import ForLoopExtractor
from soap.semantics.latency.common import LATENCY_TABLE
from soap.semantics.latency.distance import (
    dependence_vector, dependence_distance, ISLIndependenceException
)
from soap.semantics.latency.graph import (
    SequentialLatencyDependenceGraph, LoopLatencyDependenceGraph, latency_eval
)
from soap.semantics.linalg import IntegerIntervalArray, ErrorSemanticsArray
from soap.semantics.state import BoxState, MetaState
from soap.semantics.state.meta import flow_to_meta_state


class _DontCare(object):
    def __eq__(self, other):
        return self.__class__ == other.__class__

    def __hash__(self):
        return hash(self.__class__)

_ = _DontCare()


class TestDependenceCheck(unittest.TestCase):
    def setUp(self):
        self.x = Variable('x', dtype=int_type)
        self.y = Variable('y', dtype=int_type)
        self.z = Variable('z', dtype=int_type)
        self.sx = slice(0, 9, 1)
        self.sy = slice(1, 10, 1)

    def test_simple_subscripts(self):
        source = Subscript(
            expression_factory(operators.ADD_OP, self.x, IntegerInterval(1)))
        sink = Subscript(self.x)
        dist_vect = dependence_vector([self.x], [self.sx], {}, source, sink)
        self.assertEqual(dist_vect, (1, ))
        dist = dependence_distance(dist_vect, [self.sx])
        self.assertEqual(dist, 1)

    def test_simple_independence(self):
        source = Subscript(
            expression_factory(operators.ADD_OP, self.x, IntegerInterval(20)))
        sink = Subscript(self.x)
        self.assertRaises(
            ISLIndependenceException, dependence_vector,
            [self.x], [self.sx], {}, source, sink)

    def test_multi_dim_subscripts(self):
        """
        Test case::
            for (x in 0...9) {
                for (y in 1...9) {
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
            [self.x, self.y], iter_slices, {}, source, sink)
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
            [self.x], [self.sx], {}, source, sink)

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
        dist_vect = dependence_vector([self.x], [self.sx], {}, source, sink)
        self.assertEqual(dist_vect, (1, ))

    def test_variable_in_subscripts(self):
        """
        for (x in 0...9) { a[x + z] = a[x]; }
        """
        expr = expression_factory(operators.ADD_OP, self.x, self.z)
        source = Subscript(expr)
        sink = Subscript(self.x)
        invariant = {
            self.z: IntegerInterval([3, 10])
        }
        dist_vect = dependence_vector(
            [self.x], [self.sx], invariant, source, sink)
        self.assertEqual(dist_vect, (3, ))


class _VariableLabelMixin(unittest.TestCase):
    def setUp(self):
        self.ori_ii_prec = context.ii_precision
        context.ii_precision = 30
        self.w = Variable('w', real_type)
        self.x = Variable('x', real_type)
        self.y = Variable('y', real_type)
        self.z = Variable('z', real_type)
        self.a = Variable('a', RealArrayType([30]))
        self.b = Variable('b', RealArrayType([30, 30]))
        self.i = Variable('i', int_type)
        self.j = Variable('j', int_type)
        self.dummy_error = ErrorSemantics(1)
        self.lw = Label(self.w, self.dummy_error, _)
        self.lx = Label(self.x, self.dummy_error, _)
        self.ly = Label(self.y, self.dummy_error, _)
        self.lz = Label(self.z, self.dummy_error, _)
        self.dummy_array = ErrorSemanticsArray([1] * 30)
        self.dummy_multi_array = ErrorSemanticsArray([[1] * 30] * 30)
        self.la = Label(self.a, self.dummy_array, _)
        self.lb = Label(self.b, self.dummy_multi_array, _)
        self.dummy_int = IntegerInterval(1)
        self.li = Label(self.i, self.dummy_int, _)
        self.lj = Label(self.j, self.dummy_int, _)
        self.dummy_subscript = IntegerIntervalArray([1])

    def tearDown(self):
        context.ii_precision = self.ori_ii_prec


class TestSequentialLatencyDependenceGraph(_VariableLabelMixin):
    def test_simple_dag_latency(self):
        expr_1 = expression_factory(operators.MULTIPLY_OP, self.lw, self.lx)
        expr_2 = expression_factory(operators.ADD_OP, self.ly, self.lz)
        label_1 = Label(expr_1, self.dummy_error, _)
        label_2 = Label(expr_2, self.dummy_error, _)
        expr_3 = expression_factory(operators.SUBTRACT_OP, label_1, label_2)
        label_3 = Label(expr_3, self.dummy_error, _)

        env = {
            self.x: label_3,
            self.y: label_1,
            label_1: expr_1,
            label_2: expr_2,
            label_3: expr_3,
            self.lw: self.w,
            self.lx: self.x,
            self.ly: self.y,
            self.lz: self.z,
        }

        graph = SequentialLatencyDependenceGraph(env, None, [self.x, self.y])
        latency = graph.latency()
        expect_latency = LATENCY_TABLE[real_type, operators.ADD_OP]
        expect_latency += LATENCY_TABLE[real_type, operators.SUBTRACT_OP]
        self.assertEqual(latency, expect_latency)


class TestLoopLatencyDependenceGraph(_VariableLabelMixin):
    def setUp(self):
        super().setUp()
        bool_label = Label(_, _, _)
        bool_env = {
            bool_label: BinaryBoolExpr(
                operators.LESS_OP, self.li, IntegerInterval(10)),
            self.li: self.i,
        }
        self.bool_expr = LabelSemantics(bool_label, bool_env)
        self.invariant = {self.i: IntegerInterval([0, 9])}

    def test_variable_initiation(self):
        expr = expression_factory(
            operators.ADD_OP, self.lx, self.dummy_error)
        label = Label(expr, self.dummy_error, _)
        iter_expr = expression_factory(
            operators.ADD_OP, self.li, self.dummy_int)
        iter_label = Label(expr, self.dummy_int, _)
        env = {
            self.x: label,
            label: expr,
            self.lx: self.x,
            self.i: iter_label,
            iter_label: iter_expr,
            self.li: self.i,
        }
        fix_expr = FixExpr(self.bool_expr, env, self.x, _)
        graph = LoopLatencyDependenceGraph(fix_expr, self.invariant)
        ii = graph.initiation_interval()
        expect_ii = LATENCY_TABLE[real_type, operators.ADD_OP]
        self.assertAlmostEqual(ii, expect_ii)
        trip_count = graph.latency()
        expect_trip_count = 9 * ii + expect_ii
        self.assertEqual(trip_count, expect_trip_count)

    def test_array_independence_initiation(self):
        sub_expr = expression_factory(operators.SUBSCRIPT_OP, self.li)
        sub_label = Label(sub_expr, self.dummy_subscript, _)
        acc_expr = expression_factory(
            operators.INDEX_ACCESS_OP, self.la, sub_label)
        acc_label = Label(acc_expr, self.dummy_error, _)
        inc_expr = expression_factory(operators.ADD_OP, acc_label, self.li)
        inc_label = Label(inc_expr, self.dummy_error, _)
        upd_expr = expression_factory(
            operators.INDEX_UPDATE_OP, self.la, sub_label, inc_label)
        upd_label = Label(upd_expr, self.dummy_array, _)
        step_expr = expression_factory(
            operators.ADD_OP, self.li, IntegerInterval(1))
        step_label = Label(step_expr, self.dummy_int, _)
        env = {
            self.a: upd_label,
            self.i: step_label,
            sub_label: sub_expr,
            upd_label: upd_expr,
            inc_label: inc_expr,
            acc_label: acc_expr,
            step_label: step_expr,
            self.la: self.a,
            self.li: self.i,
        }
        fix_expr = FixExpr(self.bool_expr, env, self.a, _)
        graph = LoopLatencyDependenceGraph(fix_expr, self.invariant)
        ii = graph.initiation_interval()
        expect_ii = 1
        self.assertEqual(ii, expect_ii)

    def test_simple_array_initiation(self):
        """
        for (i in ...) { a[i] = a[i - j] + i; }
        """
        idx_expr = expression_factory(operators.SUBTRACT_OP, self.li, self.lj)
        idx_label = Label(idx_expr, self.dummy_int, _)
        snk_expr = expression_factory(operators.SUBSCRIPT_OP, idx_label)
        snk_label = Label(snk_expr, self.dummy_subscript, _)
        src_expr = expression_factory(operators.SUBSCRIPT_OP, self.li)
        src_label = Label(src_expr, self.dummy_subscript, _)
        acc_expr = expression_factory(
            operators.INDEX_ACCESS_OP, self.la, snk_label)
        acc_label = Label(acc_expr, self.dummy_error, _)
        inc_expr = expression_factory(operators.ADD_OP, acc_label, self.li)
        inc_label = Label(inc_expr, self.dummy_error, _)
        upd_expr = expression_factory(
            operators.INDEX_UPDATE_OP, self.la, src_label, inc_label)
        upd_label = Label(upd_expr, self.dummy_array, _)
        step_expr = expression_factory(
            operators.ADD_OP, self.li, IntegerInterval(1))
        step_label = Label(step_expr, self.dummy_int, _)
        env = {
            self.a: upd_label,
            self.i: step_label,
            self.j: self.lj,
            snk_label: snk_expr,
            src_label: src_expr,
            idx_label: idx_expr,
            upd_label: upd_expr,
            inc_label: inc_expr,
            acc_label: acc_expr,
            step_label: step_expr,
            self.la: self.a,
            self.li: self.i,
            self.lj: self.j,
        }
        fix_expr = FixExpr(self.bool_expr, env, self.a, _)
        invariant = {
            self.i: IntegerInterval([0, 9]),
            self.j: IntegerInterval([3, 5]),
        }
        graph = LoopLatencyDependenceGraph(fix_expr, invariant)
        ii = graph.initiation_interval()
        expect_ii = LATENCY_TABLE[real_type, operators.INDEX_ACCESS_OP]
        expect_ii += LATENCY_TABLE[real_type, operators.ADD_OP]
        expect_ii += LATENCY_TABLE[ArrayType, operators.INDEX_UPDATE_OP]
        expect_ii /= float(invariant[self.j].min)
        self.assertAlmostEqual(ii, expect_ii)

    def test_multi_dim_array_initiation(self):
        pass

    def test_mixed_initiation(self):
        pass

    def test_full_flow(self):
        program = """
        real[30] a;
        int i = 0;
        while (i < 10) {
            a[i + 3] = a[i] + i;
            i = i + 1;
        };
        """
        meta_state = flow_to_meta_state(parse(program))
        state = BoxState({
            self.a: ErrorSemanticsArray(
                [ErrorSemantics([0, 10 * i], [0, 0]) for i in range(30)]),
        })
        distance = 3
        trip_count = 10
        latency = latency_eval(meta_state, state, [self.a])
        depth = LATENCY_TABLE[real_type, operators.INDEX_ACCESS_OP]
        depth += LATENCY_TABLE[real_type, operators.ADD_OP]
        depth += LATENCY_TABLE[ArrayType, operators.INDEX_UPDATE_OP]
        expect_ii = depth / distance
        expect_latency = expect_ii * (trip_count - 1) + depth
        self.assertAlmostEqual(latency, expect_latency)

    def test_loop_nest_flow(self):
        program = """
        real[30] a;
        int j = 0;
        int i = 0;
        while (j < 10) {
            while (i < 10) {
                a[i + j] = a[i] + i;
                i = i + 1;
            };
            j = j + 1;
        };
        """
        meta_state = flow_to_meta_state(parse(program))
        state = BoxState({
            self.a: ErrorSemanticsArray(
                [ErrorSemantics([0, 10 * i], [0, 0]) for i in range(30)]),
        })
        # latency = latency_eval(meta_state[self.a], state, [self.a])
        # print(latency)

    def test_multi_dim_flow(self):
        program = """
        real[30, 30] b;
        int i = 0;
        int j = 3;
        while (i < 10) {
            b[i + j, j] = b[i, j] + j;
            i = i + 1;
        };
        """
        meta_state = flow_to_meta_state(parse(program))
        state = BoxState({
            self.b: ErrorSemanticsArray(30 * [
                [ErrorSemantics([0, 10 * i], [0, 0]) for i in range(30)]]),
        })
        latency = latency_eval(meta_state[self.b], state, [self.b])
        print(latency)


class TestLoopNestExtraction(_VariableLabelMixin):
    def test_simple_loop(self):
        sub_expr = expression_factory(operators.SUBSCRIPT_OP, self.li)
        sub_label = Label(sub_expr, _, _)
        acc_expr = expression_factory(
            operators.INDEX_ACCESS_OP, self.la, sub_label)
        acc_label = Label(acc_expr, self.dummy_error, _)
        inc_expr = expression_factory(operators.ADD_OP, acc_label, self.li)
        inc_label = Label(inc_expr, self.dummy_error, _)
        upd_expr = expression_factory(
            operators.INDEX_UPDATE_OP, self.la, sub_label, inc_label)
        upd_label = Label(upd_expr, self.dummy_array, _)
        step_expr = expression_factory(
            operators.ADD_OP, self.li, IntegerInterval(1))
        step_label = Label(step_expr, self.dummy_int, _)
        loop_state = MetaState({
            self.a: upd_label,
            self.i: step_label,
            sub_label: sub_expr,
            upd_label: upd_expr,
            inc_label: inc_expr,
            acc_label: acc_expr,
            step_label: step_expr,
            self.la: self.a,
            self.li: self.i,
        })
        bool_expr = expression_factory(
            operators.LESS_OP, self.i, IntegerInterval(10))
        bool_label = Label(bool_expr, _, _)
        bool_env = MetaState({
            bool_label: bool_expr,
            self.i: self.li,
            self.li: self.i,
        })
        bool_sem = LabelSemantics(bool_label, bool_env)
        init_state = MetaState({
            self.a: self.la,
            self.la: self.a,
            self.i: self.li,
            self.li: self.i,
        })
        fix_expr = expression_factory(
            operators.FIXPOINT_OP, bool_sem, loop_state, self.a, init_state)
        for_loop = ForLoopExtractor(
            fix_expr, {self.i: IntegerInterval([1, 9])})
        expect_for_loop = {
            'iter_var': self.i,
            'iter_slice': slice(1, 9, 1),
            'loop_var': self.a,
        }
        for key, expect_val in expect_for_loop.items():
            self.assertEqual(getattr(for_loop, key), expect_val)
