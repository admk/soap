from soap.program.graph import DependenceGraph


latency_table = {
    ...
}


class LatencyDependenceGraph(DependenceGraph):
    def attr_func(self, from_node, to_node):
        expr = self.env[from_node]
        latency = latency_table[expr.op]
        dependence_type = None
        distance = 1
        attr_dict = {
            'type': dependence_type,
            'latency': latency,
            'distance': distance,
        }
        return (from_node, to_node, attr_dict)
