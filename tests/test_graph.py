import unittest

from soap.parser import parse
from soap.program.graph import (
    CyclicGraphException, DependencyGraph, sorted_vars
)
from soap.semantics import flow_to_meta_state
from soap.semantics.functions.label import label
from soap.semantics.label import Label
from soap.semantics.state import BoxState


class TestUtilityFunctions(unittest.TestCase):
    def test_sorted_vars_with_simple_expression(self):
        expr = parse('a + 2 + c + b')
        lab, env = label(expr, BoxState(bottom=True), None)
        dep_vars = sorted_vars(env, lab)
        self.assertEqual([parse(v) for v in ('a', 'c', 'b')], dep_vars)

    def test_sorted_vars_with_meta_state(self):
        out_vars = [parse('x'), parse('y'), parse('z')]
        _, env = label(
            flow_to_meta_state('x = x + b; y = a * x; z = b'),
            BoxState(bottom=True), out_vars)
        dep_vars = sorted_vars(env, [parse(v) for v in ('x', 'y')])
        self.assertEqual([parse(v) for v in ('x', 'b', 'a')], dep_vars)


class TestDependencyGraph(unittest.TestCase):
    def test_cycle_detect(self):
        vx = parse('x')
        la = Label('a')
        lb = Label('b')
        env = {vx: la, la: lb, lb: la}
        self.assertRaises(CyclicGraphException, DependencyGraph, env, vx)
