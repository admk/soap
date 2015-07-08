import collections
import math

from soap.common import cached
from soap.context import context
from soap.datatype import ArrayType
from soap.expression import (
    Variable, InputVariable, is_expression, operators, InputVariableTuple,
    OutputVariableTuple
)
from soap.program.graph import DependenceGraph
from soap.semantics import is_numeral
from soap.semantics.label import Label
from soap.semantics.schedule.common import DependenceType
from soap.semantics.schedule.table import (
    OperatorResourceTuple, RESOURCE_TABLE, PIPELINED_OPERATORS, LATENCY_TABLE,
    MAX_SHARE_COUNT, SHARED_DATATYPE_OPERATORS,
)


_irrelevant_types = (
    Label, Variable, InputVariableTuple, OutputVariableTuple)


@cached
def loop_graph(
        expr, round_values=None, sequentialize_loops=True, scheduler=None):
    from soap.semantics.schedule.graph.loop import LoopScheduleGraph
    return LoopScheduleGraph(
        expr, round_values=round_values,
        sequentialize_loops=sequentialize_loops, scheduler=scheduler)


class ScheduleGraph(DependenceGraph):
    latency_table = LATENCY_TABLE

    def __init__(
            self, env, out_vars, round_values=None,
            sequentialize_loops=True, scheduler=None):
        super().__init__(env, out_vars)
        self.sequentialize_loops = sequentialize_loops
        self.round_values = round_values or context.round_values
        self.scheduler = scheduler or context.scheduler

    def node_expr(self, node):
        from soap.transformer.partition import PartitionLabel
        if isinstance(node, (InputVariable, PartitionLabel)):
            return None, None, None
        if is_numeral(node) or node == self._root_node:
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

    def node_latency(self, node):
        expr, dtype, op = self.node_expr(node)
        if expr is None:
            # no expression exists for node
            return 0
        if op == operators.FIXPOINT_OP:
            # FixExpr, round to the nearest integer for integer cycle counts
            graph = loop_graph(
                node.expr(), self.round_values, self.sequentialize_loops,
                self.scheduler)
            latency = graph.latency()
            try:
                latency = int(math.ceil(latency))
            except OverflowError:
                return latency
            return int(latency)
        return self.latency_table[dtype][op]

    def node_resource(self, node):
        expr, dtype, op = self.node_expr(node)
        if expr is None:
            return {}, {}
        if op == operators.FIXPOINT_OP:
            # FixExpr
            graph = loop_graph(
                node.expr(), self.round_values, self.sequentialize_loops,
                self.scheduler)
            return graph.resource()
        if op == operators.SUBTRACT_OP:
            op = operators.ADD_OP
        res_map = {(dtype, op): 1}
        return res_map, res_map

    def edge_attr(self, from_node, to_node):
        attr_dict = {
            'type': DependenceType.flow,
            'latency': self.node_latency(to_node),
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
            node_lat = self.node_latency(node)
            for next_node in next_func(node):
                _, next_end = schedule_map.get(next_node, default_value)
                max_next_end = max(max_next_end, next_end)
            if self.sequentialize_loops:
                _, _, op = self.node_expr(node)
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
        max_lat = self.max_latency(schedule_map)
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
            _, _, op = self.node_expr(node)
            if op in PIPELINED_OPERATORS:
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

        return zip(control_point_nodes[:-1], control_point_cycles[1:])

    def control_points(self):
        return self._pivot(self.schedule())

    def max_latency(self, schedule):
        latency = 0
        for node, (begin, end) in schedule.items():
            latency = max(latency, end)
        return latency

    def latency(self):
        raise NotImplementedError('Override this method.')

    def resource(self):
        raise NotImplementedError('Override this method.')

    def resource_stats(self):
        total_map, min_alloc_map = self.resource()
        stat = OperatorResourceTuple(0, 0, 0)
        for (dtype, op), count in total_map.items():
            if (dtype, op) in SHARED_DATATYPE_OPERATORS:
                count = count / MAX_SHARE_COUNT
                if self.round_values:
                    count = int(math.ceil(count))
            if op in operators.COMPARISON_OPERATORS:
                op = 'comparison'
            count = max(count, min_alloc_map[dtype, op])
            stat += RESOURCE_TABLE[dtype][op] * count
        return stat
