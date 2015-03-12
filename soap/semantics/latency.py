import itertools

import islpy
import networkx
import numpy

from soap.expression import (
    AccessExpr, expression_factory, InputVariable, is_expression,
    is_variable, operators, UpdateExpr, Variable
)
from soap.program.graph import DependenceGraph
from soap.semantics import is_numeral
from soap.semantics.label import Label


flow_dependence_only = True


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


def _rename_var_in_expr(expr, var_list, format_str):
    if is_variable(expr):
        if expr in var_list:
            return Variable(format_str.format(expr.name), dtype=expr.dtype)
        return expr
    if is_expression(expr):
        args = (_rename_var_in_expr(a, var_list, format_str)
                for a in expr.args)
        return expression_factory(expr.op, *args)
    return expr


class ISLExpressionError(Exception):
    """Expression is mal-formed.  """


class ISLIndependenceException(Exception):
    """No dependence.  """


def _check_isl_expr(expr):
    variables = expr.vars()
    try:
        islpy.Set('{{ [{vars}]: {expr} > 0 }}'.format(
            vars=', '.join(v.name for v in variables), expr=expr))
    except islpy.Error:
        raise ISLExpressionError(
            'Expression {} is written in a format not expected by ISL.'
            .format(expr))


def dependence_distance(iter_vars, iter_bounds, loop_state, source, sink):
    """
    Uses ISL for dependence testing.

        source, sink: Subscript objects
    """
    if len(source.args) != len(sink.args):
        raise ValueError('Source/sink subscript length mismatch.')

    dist_vars = []
    constraints = []
    exists_vars = set()
    for var in iter_vars:
        dist_var = '__dist_{}'.format(var.name)
        dist_vars.append(dist_var)
        lower, upper = iter_bounds[var]
        constraints.append(
            '{dist_var} = __snk_{iter_var} - __src_{iter_var}'
            .format(dist_var=dist_var, iter_var=var))
        constraints.append(
            '{lower} <= __src_{iter_var} < __snk_{iter_var} <= {upper}'
            .format(iter_var=var, lower=lower, upper=upper))

    for src_idx, snk_idx in zip(source.args, sink.args):
        _check_isl_expr(src_idx)
        _check_isl_expr(snk_idx)
        src_idx = _rename_var_in_expr(src_idx, iter_vars, '__src_{}')
        snk_idx = _rename_var_in_expr(snk_idx, iter_vars, '__snk_{}')
        constraints.append('{} = {}'.format(src_idx, snk_idx))
        exists_vars |= src_idx.vars() | snk_idx.vars()

    for var in exists_vars:
        if var.name.startswith('__'):
            # FIXME terrible hack
            continue
        lower, upper = loop_state[var]
        constraints.append('{lower} <= {var} <= {upper}'.format(
            lower=lower, var=var, upper=upper))

    problem = '{{ [{dist_vars}] : exists ( {exists_vars} : {constraints} ) }}'
    problem = problem.format(
        dist_vars=', '.join(reversed(dist_vars)),
        iter_vars=', '.join(v.name for v in iter_vars),
        constraints=' and '.join(constraints),
        exists_vars=', '.join(v.name for v in exists_vars))

    basic_set = islpy.BasicSet(problem)
    dist_vect_list = []
    basic_set.lexmin().foreach_point(dist_vect_list.append)
    if not dist_vect_list:
        raise ISLIndependenceException
    if len(dist_vect_list) != 1:
        raise ValueError(
            'The function lexmin() should return a single point.')
    raw_dist_vect = dist_vect_list.pop()
    dist_vect = []
    for i in range(len(dist_vars)):
        val = raw_dist_vect.get_coordinate_val(islpy.dim_type.set, i)
        dist_vect.append(val.to_python())
    return tuple(reversed(dist_vect))


class DependenceType(object):
    independent = 0
    flow = 1
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
            'type': DependenceType.flow,
            'latency': 0,
            'distance': 1,
        }
        self.graph.add_edge(from_node, to_node, attr_dict)

    def _init_variable_loops(self):
        for to_node in self.graph.pred:
            if not isinstance(to_node, InputVariable):
                continue
            out_var = Variable(to_node.name, to_node.dtype)
            if out_var not in self.env:
                continue
            # variable is input & output, should have a self-loop
            self._add_variable_loop(to_node, out_var)

    _edge_type_map = {
        (operators.INDEX_ACCESS_OP, operators.INDEX_ACCESS_OP):
            DependenceType.independent,
        (operators.INDEX_ACCESS_OP, operators.INDEX_UPDATE_OP):
            DependenceType.anti,
        (operators.INDEX_UPDATE_OP, operators.INDEX_ACCESS_OP):
            DependenceType.flow,
        (operators.INDEX_UPDATE_OP, operators.INDEX_UPDATE_OP):
            DependenceType.output,
    }

    def _add_array_loop(self, from_node, to_node):
        dep_type = self._edge_type_map[from_node.op, to_node.op]

        if dep_type == DependenceType.independent:
            # RAR is not a dependence
            return
        elif dep_type == DependenceType.flow:
            latency = self._node_latency(to_node)
        elif dep_type == DependenceType.anti:
            latency = 1 - self._node_latency(from_node)
        elif dep_type == DependenceType.output:
            latency = 1 + self._node_latency(to_node)
            latency -= self._node_latency(from_node)
        else:
            raise TypeError('Unrecognized dependence type.')

        try:
            distance = dependence_distance(
                self.iter_vars, self.loop_state, self.loop_state,
                from_node.subscript, to_node.subscript)
        except ISLNoDependenceException:
            return

        attr_dict = {
            'type': dep_type,
            'latency': latency,
            'distance': distance,
        }
        self.graph.add_edge(from_node, to_node, attr_dict)

    def _init_array_loops(self):
        def is_array_op(node):
            if isinstance(node, InputVariable):
                return False
            if is_numeral(node):
                return False
            if node == self._root_node:
                return False
            expr = self.env[node]
            return isinstance(expr, (AccessExpr, UpdateExpr))

        nodes = (n for n in self.graph.nodes() if is_array_op(n))
        for from_node, to_node in itertools.product(nodes, repeat=2):
            if from_node.var != to_node.var:
                # access different arrays
                continue
            check = flow_dependence_only and not (
                from_node.op == operators.INDEX_UPDATE_OP and
                to_node.op == operators.INDEX_ACCESS_OP)
            if check:
                continue
            self._add_array_loop(from_node, to_node)

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
            'type': DependenceType.flow,
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
