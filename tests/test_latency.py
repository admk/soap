import unittest

from soap.datatype import int_type
from soap.expression import operators, BinaryArithExpr, Variable
from soap.semantics.error import IntegerInterval
from soap.semantics.label import Label
from soap.semantics.latency import LatencyDependenceGraph


class TestLatencyDependenceGraph(unittest.TestCase):
    def setUp(self):
        self.latency_table = {
            (int_type, operators.ADD_OP): 7,
            (int_type, operators.MULTIPLY_OP): 5,
            (int_type, operators.SUBTRACT_OP): 8,
        }

        class Graph(LatencyDependenceGraph):
            latency_table = self.latency_table

        self.Graph = Graph
        self.variables = {x: Variable(x, int_type) for x in 'abcdxy'}
        self.labels = {
            x: Label(v, bound=IntegerInterval(1))
            for x, v in self.variables.items()}
        self.base_env = {
            self.variables[n]: self.labels[n] for n in self.labels}
        self.base_env.update({
            self.labels[n]: self.variables[n] for n in self.labels})

    def test_simple_dag_latency(self):
        expr_1 = BinaryArithExpr(
            operators.MULTIPLY_OP, self.labels['a'], self.labels['b'])
        expr_2 = BinaryArithExpr(
            operators.ADD_OP, self.labels['c'], self.labels['d'])
        label_1 = Label(expr_1, bound=IntegerInterval(1))
        label_2 = Label(expr_2, bound=IntegerInterval(1))

        env = dict(self.base_env)
        env.update({
            self.variables['y']: label_1,
            self.labels['x']: BinaryArithExpr(
                operators.SUBTRACT_OP, label_1, label_2),
            label_1: expr_1,
            label_2: expr_2,
        })

        graph = self.Graph(env, [self.variables['x'], self.variables['y']])
        latency = graph.depth
        expect_latency = self.latency_table[int_type, operators.ADD_OP]
        expect_latency += self.latency_table[int_type, operators.SUBTRACT_OP]
        self.assertEqual(latency, expect_latency)

    def test_variable_initiation(self):
        pass
