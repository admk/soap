import collections
import functools
import itertools
import math

from soap import logger
from soap.common.cache import cached
from soap.context import context
from soap.datatype import ArrayType
from soap.expression import (
    AccessExpr, InputVariable, is_expression, operators, UpdateExpr, Variable,
    InputVariableTuple, OutputVariableTuple
)
from soap.program.graph import DependenceGraph
from soap.semantics import is_numeral
from soap.semantics.functions import label
from soap.semantics.label import Label
from soap.semantics.schedule.common import (
    DependenceType, iter_point_count,
    PIPELINED_OPERATORS, LOOP_LATENCY_TABLE, SEQUENTIAL_LATENCY_TABLE
)
from soap.semantics.schedule.extract import ForLoopNestExtractor
from soap.semantics.schedule.distance import dependence_eval
from soap.semantics.schedule.ii import rec_init_int_search, res_init_int


_irrelevant_types = (
    Label, Variable, InputVariableTuple, OutputVariableTuple)


def _resource_ceil(res_map):
    return {
        dtype_op: int(math.ceil(res_count))
        for dtype_op, res_count in res_map.items()}


def _resource_map_add(total_map, incr_map):
    for dtype_op, res_count in incr_map.items():
        total_map[dtype_op] = total_map.setdefault(dtype_op, 0) + res_count


def _resource_map_min(total_map, lower_map):
    for dtype_op, res_count in lower_map.items():
        total_map[dtype_op] = max(
            total_map.setdefault(dtype_op, 0), res_count)


class SequentialLatencyDependenceGraph(DependenceGraph):

    latency_table = SEQUENTIAL_LATENCY_TABLE
    pipelined_operators = PIPELINED_OPERATORS

    def __init__(
            self, env, out_vars, round_values=False, sequentialize_loops=True,
            scheduler=None):
        self.sequentialize_loops = sequentialize_loops
        self.round_values = round_values
        self.scheduler = scheduler or context.scheduler
        super().__init__(env, out_vars)

    def _node_expr(self, node):
        if isinstance(node, InputVariable) or is_numeral(node):
            return None, None, None
        if node == self._root_node:
            return None, None, None
        expr = self.env[node]
        if is_expression(expr):
            dtype = node.dtype
            if isinstance(dtype, ArrayType):
                dtype = ArrayType
            return expr, dtype, expr.op
        if is_numeral(expr) or isinstance(expr, _irrelevant_types):
            return None, None, None
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
        expr, dtype, op = self._node_expr(node)
        if expr is None:
            # no expression exists for node
            return 0
        if op == operators.FIXPOINT_OP:
            # FixExpr, round to the nearest integer for integer cycle counts
            latency = self._node_loop_graph(node).latency()
            try:
                latency = int(math.ceil(latency))
            except OverflowError:
                return latency
            return int(latency)
        return self.latency_table[dtype, op]

    def _node_resource(self, node):
        expr, dtype, op = self._node_expr(node)
        if expr is None:
            return {}, {}
        if op == operators.FIXPOINT_OP:
            # FixExpr
            return self._node_loop_graph(node).resource()
        if op == operators.SUBTRACT_OP:
            op = operators.ADD_OP
        res_map = {(dtype, op): 1}
        return res_map, res_map

    _array_operators = [operators.INDEX_ACCESS_OP, operators.INDEX_UPDATE_OP]

    def operator_counts(self):
        try:
            return self._operator_counts
        except AttributeError:
            pass
        operator_map = collections.defaultdict(int)
        memory_map = collections.defaultdict(int)
        for node in self.graph.nodes():
            expr, dtype, op = self._node_expr(node)
            if expr is None:
                continue
            if op in self._array_operators:
                memory_map[node.expr().true_var()] += 1
            else:
                operator_map[dtype, op] += 1
        self._operator_counts = (operator_map, memory_map)
        return self._operator_counts

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
                _, _, op = self._node_expr(node)
                if op == operators.FIXPOINT_OP:
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
            _, _, op = self._node_expr(node)
            if op in self.pipelined_operators:
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
            try:
                latency = int(math.ceil(latency))
            except OverflowError:
                latency = float('inf')
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
        if not self.is_pipelined:
            self._initiation_interval = self.depth()
        else:
            logger.debug('Pipelining ', self.fix_expr)
            _, access_map = self.operator_counts()
            res_mii = res_init_int(access_map)
            ii = rec_init_int_search(self.loop_graph, res_mii)
            if self.round_values:
                ii = int(math.ceil(ii))
            self._initiation_interval = ii
        return self._initiation_interval

    def init_graph(self):
        try:
            return self._init_graph
        except AttributeError:
            pass
        _, init_env = label(self.fix_expr.init_state, None, None)
        self._init_graph = SequentialLatencyDependenceGraph(
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

    def latency(self):
        try:
            return self._latency
        except AttributeError:
            pass
        init_latency = self.init_graph().sequential_latency()
        ii = self.initiation_interval()
        loop_latency = (self.trip_count() - 1) * ii + self.depth()
        self._latency = init_latency + loop_latency
        return self._latency

    def resource(self):
        try:
            return self._resource
        except AttributeError:
            pass
        if not self.is_pipelined:
            loop_total_map, loop_alloc_map = self.sequential_resource()
        else:
            loop_total_map = collections.defaultdict(int)
            for node in self.nodes():
                expr, dtype, op = self._node_expr(node)
                if expr is None:
                    continue
                loop_total_map[dtype, op] += 1

            loop_alloc_map = {}

        total_map, min_alloc_map = self.init_graph().sequential_resource()
        _resource_map_add(total_map, loop_total_map)
        _resource_map_min(min_alloc_map, loop_alloc_map)

        self._resource = (total_map, min_alloc_map)
        return self._resource


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
