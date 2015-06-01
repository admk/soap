import math

from soap import logger
from soap.semantics.schedule.common import resource_map_add, resource_map_min
from soap.semantics.schedule.table import LATENCY_TABLE
from soap.semantics.schedule.graph.base import ScheduleGraph


class SequentialScheduleGraph(ScheduleGraph):

    latency_table = LATENCY_TABLE

    def sequential_latency(self):
        try:
            return self._sequential_latency
        except AttributeError:
            pass
        latency = self.max_latency(self.schedule())
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
