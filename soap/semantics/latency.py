import itertools

import networkx
import numpy

from soap.expression import (
    is_expression, InputVariable, OutputVariable, Variable
)
from soap.program.graph import DependenceGraph
from soap.semantics import is_numeral
from soap.semantics.label import Label


def max_latency(graph):
    dist = {}
    nodes = networkx.topological_sort(graph)
    for to_node in nodes:
        pred_dists = [
            dist[from_node] + graph[from_node][to_node]['latency']
            for from_node in graph.pred[to_node]]
        dist[to_node] = max([0] + pred_dists)
    return max(dist.values())


def rec_ii_search(graph, init_ii=1, prec=3):
    """
    Performs a binary search of the recurrence-based minimum initiation
    interval (RecMII).
    """
    inf = float('inf')
    neg_inf = -inf
    nodes = list(graph.nodes())
    len_nodes = len(nodes)
    dist_shape = [len_nodes] * 2

    def rec_ii_check(ii):
        """
        Checks if the target II is valid.  Runs a modified Floyd-Warshall
        algorithm to test the absence of positive cycles.

        Input ii must be greater or equal to 1.
        """
        dist = numpy.full(dist_shape, neg_inf)
        iterer = itertools.product(enumerate(nodes), repeat=2)
        for (from_idx, from_node), (to_idx, to_node) in iterer:
            try:
                edge = graph[from_node][to_node]
            except KeyError:
                continue
            dist[from_idx, to_idx] = edge['latency'] - ii * edge['distance']

        iterer = itertools.product(range(len_nodes), repeat=3)
        for mid_idx, from_idx, to_idx in iterer:
            dist_val = dist[from_idx, mid_idx] + dist[mid_idx, to_idx]
            if dist_val > dist[from_idx, to_idx]:
                if from_idx == to_idx and dist_val > 0:
                    return False
                dist[from_idx, to_idx] = dist_val

        return True

    min_ii = max_ii = init_ii
    incr = prec = 2 ** -prec

    # find an upper-bound on MII
    while not rec_ii_check(max_ii):
        max_ii += incr
        incr *= 2

    # binary search for the optimal MII
    last_ii = max_ii
    while max_ii - min_ii > prec:
        mid_ii = (min_ii + max_ii) / 2
        if rec_ii_check(mid_ii):
            max_ii = last_ii = mid_ii
        else:
            min_ii = mid_ii

    return last_ii


class DependenceType(object):
    true = 1
    anti = 2
    output = 3


class LatencyDependenceGraph(DependenceGraph):

    latency_table = {
        ...
    }

    def __init__(self, env, out_vars, iter_vars=None):
        super().__init__(env, out_vars)
        self.depth = max_latency(self.graph)
        self.iter_vars = list(iter_vars or [])
        if self.iter_vars:
            self._init_variable_loops()
            self._init_array_loops()
        self.ii = None

    @property
    def is_loop_nest(self):
        return bool(self.iter_vars)

    def _add_variable_loop(self, from_node, to_node):
        attr_dict = {
            'type': DependenceType.true,
            'latency': 0,
            'distance': 1,
        }
        self.graph.add_edge(from_node, to_node, attr_dict)

    def _init_variable_loops(self):
        for to_node in self.graph.pred:
            if not isinstance(to_node, InputVariable):
                continue
            out_var = Variable(to_node.name, to_node.dtype)
            if out_var not in self.out_vars:
                continue
            # variable is input & output, should have a self-loop
            self._add_variable_loop(to_node, out_var)

    def _init_array_loops(self):
        pass

    def _node_latency(self, node):
        if isinstance(node, InputVariable):
            return 0
        if is_numeral(node):
            return 0
        expr = self.env[node]
        if is_expression(expr):
            return self.latency_table[node.dtype, expr.op]
        if isinstance(expr, (Label, Variable)):
            return 0
        raise TypeError(
            'Do not know how to compute latency for node {}'.format(node))

    def edge_attr(self, from_node, to_node):
        attr_dict = {
            'type': DependenceType.true,
            'latency': self._node_latency(to_node),
            'distance': 0,
        }
        return from_node, to_node, attr_dict

    @property
    def initiation_interval(self):
        if not self.ii:
            self.ii = rec_ii_search(self.graph)
        return self.ii


def latency_eval(expr, state, out_vars):
    from soap.semantics import BoxState, label
    if not state:
        state = BoxState(bottom=True)
    _, env = label(expr, state, out_vars)
    graph = LatencyDependenceGraph(env, out_vars)
    depth = graph.depth
    ii = graph.initiation_interval
    trip_count = ...
    return ii * (trip_count - 1) + depth
