import collections
import math

from soap import logger
from soap.expression import (
    expression_factory, AccessExpr, UpdateExpr
)
from soap.semantics.label import Label
from soap.semantics.schedule.common import resource_map_add, resource_map_min
from soap.semantics.schedule.table import LATENCY_TABLE
from soap.semantics.schedule.graph.base import ScheduleGraph


class SequentialScheduleGraph(ScheduleGraph):

    latency_table = LATENCY_TABLE

    def __init__(
            self, env, out_vars, round_values=False,
            sequentialize_loops=True, scheduler=None, loop_recurrence=None):
        super().__init__(
            env, out_vars, round_values=round_values,
            sequentialize_loops=sequentialize_loops, scheduler=scheduler)
        self.loop_recurrence = loop_recurrence

    def _loop_recurrence_latency(
            self, total_latency, schedule, loop_recurrence):
        # create a new schedule with expressions compatible with
        # loop_recurrence specification
        new_schedule = collections.defaultdict(list)
        for node, interval in schedule.items():
            expr = node
            if isinstance(node, Label):
                expr = self.env[node]
                if isinstance(expr, (AccessExpr, UpdateExpr)):
                    expr = node.expr()
                    args = expr.args[1:]
                    expr = expression_factory(expr.op, expr.true_var(), *args)
            new_schedule[expr].append(interval)

        # finds the maximum recurrence-weigthed latency
        # from any pair of from_expr and to_expr
        max_latency = 0
        for (from_expr, to_expr), distance in loop_recurrence.items():
            from_schedule = new_schedule[from_expr]
            if not from_schedule:
                continue

            begin_latency = total_latency
            for from_begin, _ in from_schedule:
                begin_latency = min(begin_latency, from_begin)

            to_schedule = new_schedule[to_expr]
            if not to_schedule:
                end_latency = total_latency
            else:
                end_latency = 0
                for _, to_end in to_schedule:
                    end_latency = max(end_latency, to_end)

            latency = end_latency - begin_latency
            if latency < 0:
                raise ValueError('Latency cannot be negative.')
            latency /= distance
            max_latency = max(max_latency, latency)

        if max_latency == 0:
            return total_latency
        return max_latency

    def sequential_latency(self):
        try:
            return self._sequential_latency
        except AttributeError:
            pass
        schedule = self.schedule()
        latency = self.max_latency(schedule)
        if self.loop_recurrence:
            latency = self._loop_recurrence_latency(
                latency, schedule, self.loop_recurrence)
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
                res_total_map, res_lower_map = self.node_resource(node)
                resource_map_add(total_map, res_total_map)
                resource_map_add(alloc_map, res_lower_map)
            resource_map_min(min_alloc_map, alloc_map)

        self._sequential_resource = (total_map, min_alloc_map)
        return self._sequential_resource

    resource = sequential_resource
