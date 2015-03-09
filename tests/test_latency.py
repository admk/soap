import unittest

from soap.datatype import real_type
from soap.expression import operators, BinaryArithExpr, Variable
from soap.semantics.error import IntegerInterval, ErrorSemantics
from soap.semantics.label import Label
from soap.semantics.latency import LatencyDependenceGraph


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
