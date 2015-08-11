import collections
import math

from soap import logger
from soap.expression import AccessExpr, UpdateExpr
from soap.semantics.label import Label, label_to_expr
from soap.semantics.schedule.common import (
    resource_map_add, resource_map_min
)
from soap.semantics.schedule.graph.base import ScheduleGraph


class SequentialScheduleGraph(ScheduleGraph):
    def __init__(
            self, env, out_vars, round_values=None,
            sequentialize_loops=True, scheduler=None, recurrences=None):
        super().__init__(
            env, out_vars, round_values=round_values,
            sequentialize_loops=sequentialize_loops, scheduler=scheduler)
        self.recurrences = recurrences

    def recurrence_latency(self):
        try:
            return self._recurrence_latency
        except AttributeError:
            pass

        from soap.transformer.partition import PartitionLabel
        # create a new schedule with expressions compatible with
        # recurrences specification
        schedule = self.schedule()
        total_latency = self.max_latency(schedule)

        new_schedule = collections.defaultdict(list)
        for node, interval in schedule.items():
            expr = node
            if isinstance(node, PartitionLabel):
                continue
            if isinstance(node, Label):
                expr = self.env[node]
            if isinstance(expr, (AccessExpr, UpdateExpr)):
                expr = label_to_expr(node)
                var = expr.true_var()
                subscript = expr.subscript
                if isinstance(expr, AccessExpr):
                    expr = AccessExpr(var, subscript)
                elif isinstance(expr, UpdateExpr):
                    expr = UpdateExpr(var, subscript, None)
            # FIXME linearize subscript into canonical forms?
            new_schedule[expr].append(interval)

        # finds the maximum recurrence-weigthed latency
        # from any pair of from_expr and to_expr
        max_latency = 0
        for from_expr, to_expr, distance in self.recurrences:
            from_schedule = new_schedule.get(from_expr)
            if from_schedule is None:
                continue

            begin_latency = total_latency
            for from_begin, _ in from_schedule:
                begin_latency = min(begin_latency, from_begin)

            to_schedule = new_schedule.get(to_expr)
            if to_schedule is None:
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

        self._recurrence_latency = max_latency
        return max_latency

    def sequential_latency(self):
        try:
            return self._sequential_latency
        except AttributeError:
            pass
        schedule = self.schedule()
        latency = self.max_latency(schedule)
        if self.round_values:
            try:
                latency = int(math.ceil(latency))
            except OverflowError:
                latency = float('inf')
        self._sequential_latency = latency
        return self._sequential_latency

    def latency(self):
        if self.recurrences:
            latency = self.recurrence_latency()
            if latency != 0:
                return latency
        return self.sequential_latency()

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
        total_active_nodes = set()
        for active_nodes, cycles in control_points:
            alloc_map = {}
            for node in active_nodes:
                res_total_map, res_lower_map = self.node_resource(node)
                if node not in total_active_nodes:
                    resource_map_add(total_map, res_total_map)
                    total_active_nodes.add(node)
                resource_map_add(alloc_map, res_lower_map)
            resource_map_min(min_alloc_map, alloc_map)

        self._sequential_resource = (total_map, min_alloc_map)
        return self._sequential_resource

    resource = sequential_resource
