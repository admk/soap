import functools
import itertools
import math

from soap import logger
from soap.datatype import int_type, ArrayType
from soap.expression import (
    AccessExpr, InputVariable, operators, UpdateExpr, Variable
)
from soap.semantics import is_numeral
from soap.semantics.functions import label
from soap.semantics.schedule.common import (
    DependenceType, iter_point_count,
    resource_ceil, resource_map_add, resource_map_min
)
from soap.semantics.schedule.extract import ForLoopNestExtractor
from soap.semantics.schedule.distance import dependence_eval
from soap.semantics.schedule.ii import rec_init_int_search, res_init_int
from soap.semantics.schedule.table import LOOP_LATENCY_TABLE
from soap.semantics.schedule.graph.sequential import SequentialScheduleGraph


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


class LoopScheduleGraph(SequentialScheduleGraph):

    latency_table = LOOP_LATENCY_TABLE

    def __init__(self, fix_expr, round_values=False, sequentialize_loops=True):
        extractor = ForLoopNestExtractor(fix_expr)
        is_pipelined = extractor.is_for_loop_nest
        iter_vars = extractor.iter_vars
        kernel = extractor.label_kernel
        out_vars = sorted(kernel, key=str)
        super().__init__(
            kernel, out_vars, round_values=round_values,
            sequentialize_loops=sequentialize_loops)
        self.is_pipelined = is_pipelined
        self.fix_expr = fix_expr
        self.iter_vars = iter_vars
        self.iter_slices = extractor.iter_slices
        self._init_loop_graph()

    def _init_loop_graph(self):
        if not self.is_pipelined:
            return
        loop_graph = self.graph.copy()
        self._init_variable_loops(loop_graph)
        self._init_array_loops(loop_graph)
        self.loop_graph = loop_graph

    def _init_variable_loops(self, loop_graph):
        for to_node in self.graph.nodes():
            if not isinstance(to_node, InputVariable):
                continue
            if isinstance(to_node.dtype, ArrayType):
                continue
            out_var = Variable(to_node.name, to_node.dtype)
            if out_var not in self.env:
                continue
            # variable is input & output, should have a self-loop
            attr_dict = {
                'type': DependenceType.flow,
                'latency': 0,
                'distance': 1,
            }
            loop_graph.add_edge(to_node, out_var, attr_dict)

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
        dep_type = _edge_type_map[from_op, to_op]

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
        if not self.is_pipelined:
            self._initiation_interval = self.depth()
        else:
            logger.debug('Pipelining ', self.fix_expr)
            _, access_map = self.resource_counts()
            res_mii = res_init_int(access_map)
            ii = rec_init_int_search(self.loop_graph, res_mii)
            if self.round_values:
                # FIXME potential over-estimation of II
                ii_overestimate_factor = 0
                ii = int(math.ceil(ii - ii_overestimate_factor))
            self._initiation_interval = ii
        return self._initiation_interval

    def init_graph(self):
        try:
            return self._init_graph
        except AttributeError:
            pass
        _, init_env = label(self.fix_expr.init_state, None, None)
        self._init_graph = SequentialScheduleGraph(
            init_env, init_env, round_values=self.round_values,
            sequentialize_loops=self.sequentialize_loops)
        return self._init_graph

    def depth(self):
        return self.sequential_latency()

    def trip_count(self):
        if not self.is_pipelined:
            return float('inf')
        trip_counts = [iter_point_count(s) for s in self.iter_slices]
        return functools.reduce(lambda x, y: x * y, trip_counts)

    def loop_latency(self):
        try:
            return self._loop_latency
        except AttributeError:
            pass
        init_latency = self.init_graph().sequential_latency()
        ii = self.initiation_interval()
        loop_latency = (self.trip_count() - 1) * ii + self.depth()
        self._loop_latency = init_latency + loop_latency
        return self._loop_latency

    latency = loop_latency

    def loop_resource(self):
        try:
            return self._loop_resource
        except AttributeError:
            pass
        if not self.is_pipelined:
            loop_total_map, loop_alloc_map = self.sequential_resource()
        else:
            loop_total_map, _ = self.resource_counts()
            loop_alloc_map = {}
            ii = self.initiation_interval()
            loop_alloc_map = {
                dtype_op: count / ii
                for dtype_op, count in loop_total_map.items()}
            if self.round_values:
                resource_ceil(loop_alloc_map)
            # add additional adders for incrementing loop nest iterators
            resource_map_add(loop_total_map, {
                (int_type, operators.ADD_OP): len(self.iter_vars) - 1,
            })

        total_map, min_alloc_map = self.init_graph().sequential_resource()
        resource_map_add(total_map, loop_total_map)
        resource_map_min(min_alloc_map, loop_alloc_map)

        self._loop_resource = (total_map, min_alloc_map)
        return self._loop_resource

    resource = loop_resource
