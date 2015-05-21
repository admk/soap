import collections
import itertools

import numpy

from soap.context import context
from soap.datatype import ArrayType
from soap.expression import is_expression, operators
from soap.semantics import Label


neg_inf = -float('inf')


def rec_init_int_check(graph, ii):
    """
    Checks if the target II is valid.  Runs a modified Floyd-Warshall
    algorithm to test the absence of positive cycles.

    Input ii must be greater or equal to 1.
    """
    nodes = graph.nodes()
    len_nodes = len(nodes)
    dist_shape = [len_nodes] * 2

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


def rec_init_int_search(graph, init_ii=1, prec=None):
    """
    Performs a binary search of the recurrence-based minimum initiation
    interval (RecMII).
    """
    if not prec:
        prec = context.ii_precision

    min_ii = max_ii = init_ii
    incr = prec = 2 ** -prec

    # find an upper-bound on MII
    while not rec_init_int_check(graph, max_ii):
        max_ii += incr
        incr *= 2

    # binary search for the optimal MII
    last_ii = max_ii
    while max_ii - min_ii > prec:
        mid_ii = (min_ii + max_ii) / 2
        if rec_init_int_check(graph, mid_ii):
            max_ii = last_ii = mid_ii
        else:
            min_ii = mid_ii

    return last_ii


def res_init_int(latency_graph):
    port_count = context.port_count
    graph = latency_graph.graph

    resource_per_loop = collections.defaultdict(int)
    for node in graph.nodes():
        if not isinstance(node, Label):
            continue
        expr = node.expr()
        if not is_expression(expr):
            continue
        dtype = node.dtype
        if isinstance(dtype, ArrayType):
            dtype = ArrayType
        op = expr.op
        if op == operators.INDEX_ACCESS_OP or op == operators.INDEX_UPDATE_OP:
            resource_per_loop[expr.true_var()] += 1

    if not resource_per_loop:
        return 1
    ii = None
    for var, access_count in resource_per_loop.items():
        curr_ii = access_count / port_count
        ii = curr_ii if ii is None else min(curr_ii, ii)
    return max(1, ii)
