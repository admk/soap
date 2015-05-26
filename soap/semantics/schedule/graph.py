import collections
import functools
import itertools
import math

from soap import logger
from soap.common.cache import cached
from soap.context import context
from soap.datatype import ArrayType
from soap.expression import (
    AccessExpr, InputVariable, is_expression, operators, FixExpr, UpdateExpr,
    Variable, InputVariableTuple, OutputVariableTuple
)
from soap.program.graph import DependenceGraph
from soap.semantics import is_numeral, inf
from soap.semantics.functions import label
from soap.semantics.label import Label
from soap.semantics.schedule.common import (
    DependenceType, iter_point_count,
    LOOP_LATENCY_TABLE, SEQUENTIAL_LATENCY_TABLE
)
from soap.semantics.schedule.extract import ForLoopNestExtractor
from soap.semantics.schedule.distance import dependence_eval
from soap.semantics.schedule.ii import rec_init_int_search, res_init_int


_irrelevant_types = (
    Label, Variable, InputVariableTuple, OutputVariableTuple)


def _resource_map_add(total_map, incr_map):
    for dtype_op, res_count in incr_map.items():
        total_map[dtype_op] = total_map.setdefault(dtype_op, 0) + res_count


def _resource_map_min(total_map, lower_map):
    for dtype_op, res_count in lower_map.items():
        total_map[dtype_op] = max(
            total_map.setdefault(dtype_op, 0), res_count)


class SequentialLatencyDependenceGraph(DependenceGraph):

    latency_table = SEQUENTIAL_LATENCY_TABLE

    def __init__(
            self, env, out_vars, round_values=False, sequentialize_loops=True,
            scheduler=None):
        self.sequentialize_loops = sequentialize_loops
        self.round_values = round_values
        self.scheduler = scheduler or context.scheduler
        super().__init__(env, out_vars)

    def _node_expr(self, node):
        if isinstance(node, InputVariable) or is_numeral(node):
            return
        expr = self.env[node]
        if is_expression(expr):
            return expr
        if is_numeral(expr) or isinstance(expr, _irrelevant_types):
            return
        raise TypeError(
            'Do not know how to find expression for node {}'.format(node))

    def _node_loop_graph(self, node):
        try:
            cache = self._graph_cache
        except AttributeError:
            self._graph_cache = cache = {}

        graph = cache.get(node)
        if graph is not None:
            return graph
        graph = LoopLatencyDependenceGraph(
            node.expr(), round_values=self.round_values,
            sequentialize_loops=self.sequentialize_loops)
        cache[node] = graph
        return graph

    def _node_latency(self, node):
        expr = self._node_expr(node)
        if expr is None:
            # no expression exists for node
            return 0
        op = expr.op
        if op == operators.FIXPOINT_OP:
            # FixExpr
            return self._node_loop_graph(node).latency()
        dtype = node.dtype
        if isinstance(dtype, ArrayType):
            dtype = ArrayType
        return self.latency_table[dtype, expr.op]

    def _node_resource(self, node):
        expr = self._node_expr(node)
        if expr is None:
            return {}, {}
        op = expr.op
        if op == operators.FIXPOINT_OP:
            # FixExpr
            return self._node_loop_graph(node).resource()
        dtype = node.dtype
        if isinstance(dtype, ArrayType):
            dtype = ArrayType
        if op == operators.SUBTRACT_OP:
            op = operators.ADD_OP
        res_map = {(dtype, op): 1}
        return res_map, res_map

    def edge_attr(self, from_node, to_node):
        attr_dict = {
            'type': DependenceType.flow,
            'latency': self._node_latency(to_node),
            'distance': 0,
        }
        return from_node, to_node, attr_dict

    def _list_schedule(self, node_order, next_func):
        schedule_map = {}
        max_loop_end = 0
        for node in node_order:
            if isinstance(node, InputVariable) or is_numeral(node):
                continue
            default_value = (0, 0)
            max_next_end = 0
            node_lat = self._node_latency(node)
            for next_node in next_func(node):
                _, next_end = schedule_map.get(next_node, default_value)
                max_next_end = max(max_next_end, next_end)
            if self.sequentialize_loops:
                if isinstance(self._node_expr(node), FixExpr):
                    # Vivado HLS sequentiallizes loops
                    max_next_end = max(max_next_end, max_loop_end)
                    max_loop_end = max_next_end + node_lat
            schedule_map[node] = (max_next_end, max_next_end + node_lat)
        return schedule_map

    def asap_schedule(self):
        return self._list_schedule(self.dfs_postorder(), self.graph.successors)

    def alap_schedule(self):
        # schedule nodes in reverse order
        schedule_map = self._list_schedule(
            self.dfs_preorder(), self.graph.predecessors)
        # reverse begin and end
        max_lat = self._max_latency(schedule_map)
        for node, (begin, end) in schedule_map.items():
            schedule_map[node] = (max_lat - end, max_lat - begin)
        return schedule_map

    def schedule(self):
        try:
            return self._schedule
        except AttributeError:
            pass
        if self.scheduler == 'asap':
            self._schedule = self.asap_schedule()
        elif self.scheduler == 'alap':
            self._schedule = self.alap_schedule()
        return self._schedule

    def _pivot(self, schedule):
        begin_events = collections.defaultdict(set)
        end_events = collections.defaultdict(set)
        for node, (begin, end) in schedule.items():
            begin_events[begin].add(node)
            if not isinstance(self._node_expr(node), FixExpr):
                # operations are pipelineable, so only count the first cycle
                # when they expect inputs
                end = min(end, begin + 1)
            end_events[end].add(node)

        control_point_nodes = []
        control_point_cycles = []
        prev_event_cycle = 0
        active_nodes = set()
        while end_events:
            begin_min = min(begin_events)
            end_min = min(end_events)
            curr_event_cycle = min(begin_min, end_min)

            if begin_min == curr_event_cycle:
                active_nodes |= begin_events[begin_min]
                del begin_events[begin_min]
            if end_min == curr_event_cycle:
                active_nodes -= end_events[end_min]
                del end_events[end_min]

            control_point_cycles.append(curr_event_cycle - prev_event_cycle)
            control_point_nodes.append(set(active_nodes))
            prev_event_cycle = curr_event_cycle

        if begin_events or active_nodes:
            raise ValueError('Unprocessed events.')
        if curr_event_cycle != self.latency():
            raise ValueError('End of events should be the total latency.')

        return zip(control_point_nodes[:-1], control_point_cycles[1:])

    def control_points(self):
        return self._pivot(self.schedule())

    def _max_latency(self, schedule):
        latency = 0
        for node, (begin, end) in schedule.items():
            latency = max(latency, end)
        return latency

    def sequential_latency(self):
        try:
            return self._sequential_latency
        except AttributeError:
            pass
        latency = self._max_latency(self.schedule())
        if self.round_values:
            latency = int(math.ceil(latency))
        self._sequential_latency = latency
        return self._sequential_latency

    latency = sequential_latency

    def sequential_resource(self):
        try:
            return self._sequential_resource
        except AttributeError:
            pass

        min_alloc_map = {}
        total_map = {}
        for active_nodes, cycles in self.control_points():
            alloc_map = {}
            for node in active_nodes:
                res_total_map, res_lower_map = self._node_resource(node)
                _resource_map_add(total_map, res_total_map)
                _resource_map_add(alloc_map, res_lower_map)
            _resource_map_min(min_alloc_map, alloc_map)

        self._sequential_resource = (total_map, min_alloc_map)
        return self._sequential_resource

    resource = sequential_resource


class LoopLatencyDependenceGraph(SequentialLatencyDependenceGraph):

    latency_table = LOOP_LATENCY_TABLE

    def __init__(self, fix_expr, round_values=False, sequentialize_loops=True):
        extractor = ForLoopNestExtractor(fix_expr)
        loop_var = fix_expr.loop_var
        if isinstance(loop_var, OutputVariableTuple):
            out_vars = loop_var.args
        else:
            out_vars = [loop_var]
        super().__init__(
            extractor.label_kernel, out_vars, round_values=round_values,
            sequentialize_loops=sequentialize_loops)
        self.is_pipelined = extractor.is_for_loop_nest
        self.fix_expr = fix_expr
        self.iter_vars = extractor.iter_vars
        self.iter_slices = extractor.iter_slices
        self._init_loop_graph()

    def _init_loop_graph(self):
        if not self.is_pipelined:
            return
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
            ii = rec_init_int_search(self.loop_graph, res_mii)
            if self.round_values:
                ii = int(math.ceil(ii))
            self._initiation_interval = ii
        else:
            self._initiation_interval = self.depth()
        return self._initiation_interval

    def init_depth(self):
        try:
            return self._init_depth
        except AttributeError:
            pass
        _, init_env = label(self.fix_expr.init_state, None, None)
        init_graph = SequentialLatencyDependenceGraph(
            init_env, init_env, round_values=self.round_values,
            sequentialize_loops=self.sequentialize_loops)
        self._init_depth = init_graph.sequential_latency()
        return self._init_depth

    def depth(self):
        try:
            return self._depth
        except AttributeError:
            pass
        self._depth = self.sequential_latency()
        return self._depth

    def trip_count(self):
        if not self.is_pipelined:
            return inf
        trip_counts = [iter_point_count(s) for s in self.iter_slices]
        return functools.reduce(lambda x, y: x * y, trip_counts)

    def latency(self):
        try:
            return self._latency
        except AttributeError:
            pass
        ii = self.initiation_interval()
        loop_latency = (self.trip_count() - 1) * ii + self.depth()
        self._latency = self.init_depth() + loop_latency
        return self._latency

    def resource(self):
        try:
            return self._resource
        except AttributeError:
            pass


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
