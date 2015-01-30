import networkx

from soap.expression import (
    is_expression, Variable, InputVariable, External,
    InputVariableTuple, OutputVariableTuple, FixExpr
)
from soap.semantics import is_numeral, Label, LabelSemantics, MetaState


def expression_dependencies(expr):
    # find dependent variables for the corresponding expression
    if expr is None:
        # can't find expression for var or var is an input variable, so
        # there are no dependencies for it
        return []
    if isinstance(expr, FixExpr):
        # is fixpoint expression, find external dependencies in init_state
        deps = []
        for v in expr.init_state.values():
            if not isinstance(v, External):
                continue
            deps.append(v.var)
        return deps
    if isinstance(expr, External):
        # external dependencies taken care of by FixExpr dependencies.
        return []
    if is_expression(expr):
        deps = []
        for arg in expr.args:
            if isinstance(arg, InputVariableTuple):
                deps += list(arg)
            else:
                deps.append(arg)
        return deps
    if isinstance(expr, Label) or is_numeral(expr):
        # is a label/constant, dependency is itself
        return [expr]
    if isinstance(expr, Variable):
        return [InputVariable(expr.name)]
    if isinstance(expr, OutputVariableTuple):
        return list(expr.args)
    if isinstance(expr, (dict, MetaState)):
        return [expr]
    if isinstance(expr, LabelSemantics):
        return [expr]
    raise TypeError(
        'Do not know how to find dependencies in expression {!r}'
        .format(expr))


class CyclicGraphException(Exception):
    pass


class DependenceGraph(networkx.DiGraph):
    """Discovers the graph of dependences"""
    def __init__(self, env, out_vars, attr_func=None):
        super().__init__()
        self.env = env
        self.out_vars = OutputVariableTuple(out_vars)
        self.attr_func = attr_func or self._default_attr_func
        self._closure_graph = None
        self._edges_recursive(self.out_vars)

    def is_cyclic(self):
        return bool(networkx.simple_cycles(self))

    def _default_attr_func(self, from_node, to_node):
        return (from_node, to_node, {})

    def _edges_recursive(self, out_vars):
        if isinstance(out_vars, OutputVariableTuple):
            # terminal node
            deps = out_vars.args
            self.add_edges_from(
                self.attr_func(out_vars, dep_var) for dep_var in deps)
        else:
            deps = []
            for var in out_vars:
                if is_numeral(var) or isinstance(var, InputVariable):
                    continue
                expr = self.env.get(var)
                local_deps = expression_dependencies(expr)
                deps += local_deps
                self.add_edges_from(
                    self.attr_func(var, dep_var) for dep_var in local_deps)
        if deps:
            self._edges_recursive(deps)

    def input_vars(self):
        return (v for v in self.nodes() if isinstance(v, InputVariable))

    def dfs_postorder(self):
        return networkx.dfs_postorder_nodes(self, self.out_vars)

    def is_multiply_shared(self, node):
        return len(self.predecessors(node)) > 1


class HierarchicalDependenceGraph(DependenceGraph):
    def __init__(self, env, out_var, _parent_nodes=None):
        super().__init__(env, out_var)
        self._parent_nodes = _parent_nodes
        self._flat_edges = self.edges
        self.edges, self._subgraphs = self._partition({}, self.out_var)
        self._local_nodes = None

    @property
    def flat_edges(self):
        return self._flat_edges

    @property
    def subgraphs(self):
        return self._subgraphs

    def _partition(self, subgraphs, out_var):

        def local_nodes(var):
            def all_paths_converge_to_var(dep_var, var):
                if dep_var == var:
                    return True
                prev_vars = self.prev(dep_var)
                if not prev_vars:
                    return False
                return all(all_paths_converge_to_var(prev_var, var)
                           for prev_var in prev_vars)
            sphere = set()
            local_deps = self.dependencies(var)
            for dep_var in local_deps:
                if self._parent_nodes and dep_var not in self._parent_nodes:
                    continue
                if all_paths_converge_to_var(dep_var, var):
                    sphere.add(dep_var)
            return sphere

        edges = set()
        if isinstance(out_var, InputVariableTuple):
            out_vars = list(out_var)
        else:
            out_vars = [out_var]

        for var in out_vars:
            var_locals = local_nodes(var)

            if var == self.out_var:
                # root node is not considered for partitioning, since the
                # hierarchy itself is the partitioning of it.
                subgraph = var
                subgraph_deps = self.next(var)
            elif var_locals:
                # if has local hierarchy, treat locals as a subgraph, and
                # construct its dependencies
                var_locals.add(var)
                subgraph = subgraphs.get(var)
                if not subgraph:
                    local_env = {}
                    for k, v in self.env.items():
                        if k in var_locals:
                            local_env[k] = v
                    subgraph = HierarchicalDependenceGraph(
                        local_env, var, _parent_nodes=var_locals)
                    subgraphs[var] = subgraph
                subgraph_deps = subgraph.graph_dependencies()
            else:
                # no local hierarchy, standalone node
                subgraph = var
                subgraph_deps = self.next(var)

            # recursively find subgraphs in dependencies
            for dep in subgraph_deps:
                dep_edges, subgraphs = self._partition(subgraphs, dep)
                edges |= dep_edges

            # connect subgraph to its dependencies
            for dep in subgraph_deps:
                dep = subgraphs.get(dep, dep)
                edges.add((subgraph, dep))

        return edges, subgraphs

    def graph_dependencies(self):
        edges = self.flat_edges
        ends = {node for _, node in edges}
        starts = {node for node, _ in edges}
        return ends - starts

    @property
    def local_nodes(self):
        nodes = self._local_nodes
        if nodes:
            return nodes
        self._local_nodes = {node for node, _ in self.edges}
        return self._local_nodes

    def local_order(self):
        local_nodes = self.local_nodes
        # sometimes out_vars are not generated because not in edges?
        out_vars = self.out_var
        if not isinstance(out_vars, InputVariableTuple):
            out_vars = [out_vars]
        for var in out_vars:
            if not self.flat_contains(var):
                local_nodes.add(var)
        return self.order_by_dependencies(local_nodes)

    def flat_contains(self, node):
        nodes = self.local_nodes
        for each_node in nodes:
            if isinstance(each_node, HierarchicalDependencyGraph):
                if each_node.flat_contains(node):
                    return True
            elif node == each_node:
                return True
        return False

    def __eq__(self, other):
        try:
            return self.env == other.env
        except AttributeError:
            return False

    def __hash__(self):
        return hash(tuple(self.env.items()))

    def __str__(self):
        return '{{{}}}'.format(', '.join(str(n) for n in self.local_nodes))

    def __repr__(self):
        return '{cls}({nodes})'.format(
            cls=self.__class__.__name__, nodes=self.local_nodes)
