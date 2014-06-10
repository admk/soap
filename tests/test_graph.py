import unittest

from soap.expression import parse
from soap.label import Label
from soap.program.graph import (
    DependencyGraph, CyclicGraphException, sorted_vars
)
from soap.semantics import flow_to_meta_state


class TestUtilityFunctions(unittest.TestCase):
    def test_sorted_vars_with_simple_expression(self):
        expr = parse('a + 2 + c + b')
        label, env = expr.label()
        dep_vars = sorted_vars(env, label)
        self.assertEqual([parse(v) for v in ('a', 'c', 'b')], dep_vars)

    def test_sorted_vars_with_meta_state(self):
        _, env = flow_to_meta_state('x = x + b; y = a * x; z = b').label()
        dep_vars = sorted_vars(env, [parse(v) for v in ('x', 'y')])
        self.assertEqual([parse(v) for v in ('x', 'b', 'a')], dep_vars)


class TestDependencyGraph(unittest.TestCase):
    def test_cycle_detect(self):
        la = Label('a')
        lb = Label('b')
        env = {la: lb, lb: la}
        self.assertRaises(CyclicGraphException, DependencyGraph, env, la)
