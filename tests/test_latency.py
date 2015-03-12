import unittest

from soap.datatype import int_type, real_type
from soap.expression import (
    operators, BinaryArithExpr, Variable, Subscript,
)
from soap.semantics.error import IntegerInterval, ErrorSemantics
from soap.semantics.label import Label
from soap.semantics.latency import (
    dependence_distance, LatencyDependenceGraph, ISLIndependenceException,
)


class TestDependenceDistance(unittest.TestCase):
    def setUp(self):
        self.x = Variable('x', dtype=int_type)
        self.y = Variable('y', dtype=int_type)
        self.bounds = {
            self.x: IntegerInterval([0, 9]),
            self.y: IntegerInterval([0, 9])
        }

    def test_simple_subscripts(self):
        source = Subscript(
            BinaryArithExpr(operators.ADD_OP, self.x, IntegerInterval(1)))
        sink = Subscript(self.x)
        dist = dependence_distance(
            [self.x], self.bounds, self.bounds, source, sink)
        self.assertEqual(dist, (1, ))

    def test_simple_independence(self):
        source = Subscript(
            BinaryArithExpr(operators.ADD_OP, self.x, IntegerInterval(20)))
        sink = Subscript(self.x)
        self.assertRaises(
            ISLIndependenceException, dependence_distance,
            [self.x], self.bounds, self.bounds, source, sink)

    def test_multi_dim_subscripts(self):
        expr = BinaryArithExpr(
            operators.ADD_OP, self.x, IntegerInterval(2))
        source = Subscript(expr, self.y)
        expr = BinaryArithExpr(
            operators.SUBTRACT_OP, self.y, IntegerInterval(1))
        sink = Subscript(self.x, expr)
        dist = dependence_distance(
            [self.x, self.y], self.bounds, self.bounds, source, sink)
        self.assertEqual(dist, (2, 1))

    def test_multi_dim_coupled_subscripts_independence(self):
        """
        for (x in 0...9) {
            a[x + 1, x + 2] = a[x, x]
        }
        """
        expr_1 = BinaryArithExpr(
            operators.ADD_OP, self.x, IntegerInterval(1))
        expr_2 = BinaryArithExpr(
            operators.ADD_OP, self.x, IntegerInterval(2))
        source = Subscript(expr_1, expr_2)
        sink = Subscript(self.x, self.x)
        self.assertRaises(
            ISLIndependenceException, dependence_distance,
            [self.x], self.bounds, self.bounds, source, sink)

    def test_multi_dim_coupled_subscripts_dependence(self):
        """
        for (x in 0...9) {
            a[x + 1, x + 1] = a[x, x]
        }
        """
        expr_1 = BinaryArithExpr(
            operators.ADD_OP, self.x, IntegerInterval(1))
        expr_2 = BinaryArithExpr(
            operators.ADD_OP, self.x, IntegerInterval(1))
        source = Subscript(expr_1, expr_2)
        sink = Subscript(self.x, self.x)
        dist = dependence_distance(
            [self.x], self.bounds, self.bounds, source, sink)
        self.assertEqual(dist, (1, ))

    def test_complex_subscripts(self):
        pass


class TestLatencyDependenceGraph(unittest.TestCase):
    def setUp(self):
        self.latency_table = {
            (real_type, operators.ADD_OP): 7,
            (real_type, operators.MULTIPLY_OP): 5,
            (real_type, operators.SUBTRACT_OP): 8,
        }

        class Graph(LatencyDependenceGraph):
            latency_table = self.latency_table

        self.Graph = Graph
        self.variables = {x: Variable(x, real_type) for x in 'abcdxy'}
        self.labels = {
            x: Label(v, bound=ErrorSemantics(1))
            for x, v in self.variables.items()}
        self.base_env = {
            self.variables[n]: self.labels[n] for n in self.labels}
        self.base_env.update({
            self.labels[n]: self.variables[n] for n in self.labels})

    def test_simple_dag_latency(self):
        dummy_interval = ErrorSemantics(1)
        expr_1 = BinaryArithExpr(
            operators.MULTIPLY_OP, self.labels['a'], self.labels['b'])
        expr_2 = BinaryArithExpr(
            operators.ADD_OP, self.labels['c'], self.labels['d'])
        label_1 = Label(expr_1, bound=dummy_interval)
        label_2 = Label(expr_2, bound=dummy_interval)
        expr_3 = BinaryArithExpr(
            operators.SUBTRACT_OP, label_1, label_2)
        label_3 = Label(expr_3, bound=dummy_interval)

        env = dict(self.base_env)
        env.update({
            self.variables['y']: label_1,
            self.labels['x']: label_3,
            label_1: expr_1,
            label_2: expr_2,
            label_3: expr_3,
        })

        graph = self.Graph(env, [self.variables['x'], self.variables['y']])
        latency = graph.depth
        expect_latency = self.latency_table[real_type, operators.ADD_OP]
        expect_latency += self.latency_table[real_type, operators.SUBTRACT_OP]
        self.assertEqual(latency, expect_latency)

    def test_variable_initiation(self):
        dummy_interval = ErrorSemantics(1)
        expr = BinaryArithExpr(
            operators.ADD_OP, self.labels['x'], dummy_interval)
        label = Label(expr, bound=dummy_interval)
        env = dict(self.base_env)
        env.update({
            self.variables['x']: label,
            label: expr,
        })

        out_vars = [self.variables['x']]
        graph = self.Graph(env, out_vars, iter_vars=out_vars)
        ii = graph.initiation_interval
        expect_ii = self.latency_table[real_type, operators.ADD_OP]
        self.assertAlmostEqual(ii, expect_ii, places=1)

    def test_array_none_dependence_initiation(self):
        pass

    def test_simple_array_initiation(self):
        pass

    def test_multi_dim_array_initiation(self):
        pass

    def test_mixed_initiation(self):
        pass
