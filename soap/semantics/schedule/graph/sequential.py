import collections
import math

from soap import logger
from soap.context import context
from soap.datatype import ArrayType, int_type, real_type
from soap.expression import (
    Variable, InputVariable, is_expression, operators, InputVariableTuple,
    OutputVariableTuple
)
from soap.program.graph import DependenceGraph
from soap.semantics import is_numeral
from soap.semantics.label import Label
from soap.semantics.schedule.common import (
    DependenceType, PIPELINED_OPERATORS, resource_map_add, resource_map_min
)
from soap.semantics.schedule.table import LATENCY_TABLE


_irrelevant_types = (
    Label, Variable, InputVariableTuple, OutputVariableTuple)
_float_type = {23: 'float', 52: 'double'}[context.precision]


class SequentialScheduleGraph(DependenceGraph):

    pipelined_operators = PIPELINED_OPERATORS
    latency_table = LATENCY_TABLE
    dtype_key_map = {
        int_type: 'integer',
        real_type: _float_type,
        ArrayType: 'array',
    }

    def __init__(
            self, env, out_vars, round_values=False,
            sequentialize_loops=True, scheduler=None):
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
            op = expr.op
            if op in operators.COMPARISON_OPERATORS:
                op = 'comparison'
            return expr, dtype, op
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
        from soap.semantics.schedule.graph.loop import LoopScheduleGraph
        graph = LoopScheduleGraph(
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
        dtype = self.dtype_key_map[dtype]
        return self.latency_table[dtype][op]

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

    def resource_counts(self):
        try:
            return self._resource_counts
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
                continue
            operator_map[dtype, op] += 1
            if dtype == real_type:
                continue
            for arg in expr.args:
                if not isinstance(arg, Label):
                    continue
                if arg.dtype != int_type or is_numeral(self.env[arg]):
                    continue
                operator_map[dtype, 'conversion'] += 1
        self._resource_counts = (operator_map, memory_map)
        return self._resource_counts

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
        seq_latency = self.sequential_latency()
        if seq_latency == float('inf'):
            raise OverflowError(
                'Unable to schedule nodes with infinite latency.')

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
            begin_min = min(begin_events) if begin_events else float('inf')
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
        if curr_event_cycle != seq_latency:
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

        try:
            control_points = self.control_points()
        except OverflowError:
            logger.warning('Unable to schedule code with infinite latency.')
            control_points = [({node}, 1) for node in self.nodes()]

        min_alloc_map = {}
        total_map = {}
        for active_nodes, cycles in control_points:
            alloc_map = {}
            for node in active_nodes:
                res_total_map, res_lower_map = self._node_resource(node)
                resource_map_add(total_map, res_total_map)
                resource_map_add(alloc_map, res_lower_map)
            resource_map_min(min_alloc_map, alloc_map)

        self._sequential_resource = (total_map, min_alloc_map)
        return self._sequential_resource

    resource = sequential_resource
