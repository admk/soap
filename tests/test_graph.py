import unittest

from soap.program.graph import DependencyGraph, CyclicGraphException
from soap.label.base import Label


class TestDependencyGraph(unittest.TestCase):
    def test_cycle_detect(self):
        la = Label('a')
        lb = Label('b')
        env = {la: lb, lb: la}
        self.assertRaises(CyclicGraphException, DependencyGraph, env, la)
