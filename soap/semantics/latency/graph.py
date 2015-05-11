import functools
import itertools
import math

import networkx

from soap import logger
from soap.common.cache import cached
from soap.datatype import ArrayType
from soap.expression import (
    AccessExpr, InputVariable, is_expression, operators, UpdateExpr, Variable,
    InputVariableTuple, OutputVariableTuple,
)
from soap.lattice import join
from soap.program.graph import DependenceGraph
from soap.semantics import is_numeral, Label
from soap.semantics.latency.common import (
    DependenceType, iter_point_count, LATENCY_TABLE
)
from soap.semantics.latency.extract import (
    ForLoopNestExtractor, ForLoopExtractionFailureException,
    ForLoopNestExtractionFailureException
)
from soap.semantics.latency.distance import dependence_eval
from soap.semantics.latency.ii import rec_init_int_search, res_init_int


def max_latency(graph):
    """Calculates the longest path in an acyclic graph.  """
    dist = {}
    nodes = networkx.topological_sort(graph)
    for to_node in nodes:
        pred_dists = [
            dist[from_node] + graph[from_node][to_node]['latency']
            for from_node in graph.pred[to_node]]
        dist[to_node] = max([0] + pred_dists)
    return max(dist.values())


class SequentialLatencyDependenceGraph(DependenceGraph):

    latency_table = LATENCY_TABLE

    def __init__(self, env, out_vars):
        super().__init__(env, out_vars)

    def invariant(self, node):
        if isinstance(node, OutputVariableTuple):
            return join(l.invariant for l in node)
        return node.invariant

    def _loop_latency(self, node, expr):
        return LoopLatencyDependenceGraph(node.expr()).latency()

    def _node_latency(self, node):
        if isinstance(node, InputVariable):
            return 0
        if is_numeral(node):
            return 0
        expr = self.env[node]
        if is_expression(expr):
            if expr.op == operators.FIXPOINT_OP:
                # FixExpr
                return self._loop_latency(node, expr)
            dtype = node.dtype
            if isinstance(dtype, ArrayType):
                dtype = ArrayType
            return self.latency_table[dtype, expr.op]
        if is_numeral(expr):
            return 0
        if isinstance(expr, (
                Label, Variable, InputVariableTuple, OutputVariableTuple)):
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

    def latency(self):
        try:
            return self._latency
        except AttributeError:
            self._latency = max_latency(self.graph)
            return self._latency


class LoopLatencyDependenceGraph(SequentialLatencyDependenceGraph):
    def __init__(self, fix_expr):
        is_pipelined = True
        try:
            extractor = ForLoopNestExtractor(fix_expr)
        except (ForLoopExtractionFailureException,
                ForLoopNestExtractionFailureException):
            is_pipelined = False

        loop_var = fix_expr.loop_var
        if isinstance(loop_var, OutputVariableTuple):
            out_vars = loop_var.args
        else:
            out_vars = [loop_var]

        super().__init__(extractor.label_kernel, out_vars)

        self.is_pipelined = is_pipelined
        self.fix_expr = fix_expr
        self.iter_vars = extractor.iter_vars
        self.iter_slices = extractor.iter_slices
        self._init_loop_graph()

    def _init_loop_graph(self):
        loop_graph = self.graph.copy()
        self._init_variable_loops(loop_graph)
        self._init_array_loops(loop_graph)
        self.loop_graph = loop_graph

    def _add_variable_loop(self, loop_graph, from_node, to_node):
        attr_dict = {
            'type': DependenceType.flow,
            'latency': 0,
            'distance': 1,
        }
        loop_graph.add_edge(from_node, to_node, attr_dict)

    def _init_variable_loops(self, loop_graph):
        for to_node in self.graph.pred:
            if not isinstance(to_node, InputVariable):
                continue
            if isinstance(to_node.dtype, ArrayType):
                continue
            out_var = Variable(to_node.name, to_node.dtype)
            if out_var not in self.env:
                continue
            # variable is input & output, should have a self-loop
            self._add_variable_loop(loop_graph, to_node, out_var)

    _edge_type_map = {
        (operators.INDEX_ACCESS_OP, operators.INDEX_ACCESS_OP):
            DependenceType.independent,
        (operators.INDEX_ACCESS_OP, operators.INDEX_UPDATE_OP):
            DependenceType.flow,
        (operators.INDEX_UPDATE_OP, operators.INDEX_ACCESS_OP):
            DependenceType.anti,
        (operators.INDEX_UPDATE_OP, operators.INDEX_UPDATE_OP):
            DependenceType.output,
    }

    def _add_array_loop(self, loop_graph, from_node, to_node):
        # we do it for flow dependence only WAR and WAW are not dependences
        # that impact II, as read/write accesses can always be performed
        # consecutively.
        from_expr = from_node.expr()
        to_expr = to_node.expr()
        if from_expr.true_var() != to_expr.true_var():
            # access different arrays
            return

        from_op, to_op = from_expr.op, to_expr.op
        check = (from_op == operators.INDEX_ACCESS_OP and
                 to_op == operators.INDEX_UPDATE_OP)
        if not check:
            return
        dep_type = self._edge_type_map[from_op, to_op]

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

        source_expr = to_expr.subscript
        sink_expr = from_expr.subscript
        distance = dependence_eval(
            self.iter_vars, self.iter_slices, source_expr, sink_expr)
        if distance is None:
            # no dependence
            return

        attr_dict = {
            'type': dep_type,
            'latency': latency,
            'distance': distance,
        }
        loop_graph.add_edge(from_node, to_node, attr_dict)

    def _init_array_loops(self, loop_graph):
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
        for from_node, to_node in itertools.combinations(nodes, 2):
            self._add_array_loop(loop_graph, from_node, to_node)
            self._add_array_loop(loop_graph, to_node, from_node)

    def initiation_interval(self):
        try:
            return self._initiation_interval
        except AttributeError:
            pass
        if self.is_pipelined:
            logger.debug('Pipelining ', self.fix_expr)
            res_mii = res_init_int(self)
            self._initiation_interval = rec_init_int_search(
                self.loop_graph, res_mii)
        else:
            self._initiation_interval = self.depth()
        return self._initiation_interval

    def depth(self):
        try:
            return self._depth
        except AttributeError:
            self._depth = max_latency(self.graph)
            return self._depth

    def trip_count(self):
        trip_counts = [iter_point_count(s) for s in self.iter_slices]
        return functools.reduce(lambda x, y: x * y, trip_counts)

    def latency(self):
        try:
            return self._latency
        except AttributeError:
            pass
        ii = self.initiation_interval()
        self._latency = (self.trip_count() - 1) * ii + self.depth()
        return self._latency

    def true_latency(self):
        ii = math.ceil(self.initiation_interval())
        return (self.trip_count() - 1) * ii + self.depth()


@cached
def latency_graph(expr, out_vars=None):
    from soap.semantics import label
    label, env = label(expr, None, out_vars)
    if is_expression(expr):
        # expressions do not have out_vars, but have an output, in this case
        # ``label`` is its output variable
        out_vars = [label]
    return SequentialLatencyDependenceGraph(env, out_vars)


def latency_eval(expr, out_vars=None):
    return latency_graph(expr, out_vars).latency()
