import networkx

from soap.common.base import base_dispatcher
from soap.expression import InputVariable, External, InputVariableTuple
from soap.semantics import is_numeral


class ExpressionDependencies(base_dispatcher()):
    """
    Find dependent variables for the corresponding expression
    """
    def generic_execute(self, expr):
        raise TypeError(
            'Do not know how to find dependencies in expression {!r}'
            .format(expr))

    def _execute_atom(self, expr):
        return [expr]

    execute_Label = execute_numeral = _execute_atom

    def execute_Variable(self, expr):
        return [InputVariable(expr.name, expr.dtype)]

    def _execute_expression(self, expr):
        return list(expr.args)

    execute_UnaryArithExpr = execute_BinaryArithExpr = _execute_expression
    execute_UnaryBoolExpr = execute_BinaryBoolExpr = _execute_expression
    execute_SelectExpr = execute_Subscript = _execute_expression
    execute_AccessExpr = execute_UpdateExpr = _execute_expression

    def execute_FixExpr(self, expr):
        # is fixpoint expression, find external dependencies in init_state
        deps = []
        for v in expr.init_state.values():
            if not isinstance(v, External):
                continue
            deps.append(v.var)
        return deps

    def execute_External(self, expr):
        # external dependencies taken care of by FixExpr dependencies.
        return []

    execute_InputVariableTuple = _execute_expression
    execute_OutputVariableTuple = _execute_atom
    execute_MetaState = execute_LabelSemantics = _execute_atom


expression_dependencies = ExpressionDependencies()


class DependenceGraph(object):
    """Discovers the graph of dependences"""
    class _RootNode(object):
        def __str__(self):
            return '<root>'
        __repr__ = __str__

    def __init__(self, env, out_vars):
        super().__init__()
        self._invalidate_cache()
        self.graph = networkx.DiGraph()
        self.env = env
        new_out_vars = []
        for var in out_vars:
            if var not in new_out_vars:
                new_out_vars.append(var)
        self.out_vars = new_out_vars
        self._closure_graph = None
        self._root_node = self._RootNode()
        self._edges_recursive(self._root_node)

    def _invalidate_cache(self):
        self._nodes = None
        self._edges = None

    def nodes(self):
        if self._nodes is None:
            self._nodes = self.graph.nodes()
        return self._nodes

    def edges(self):
        if self._edges is None:
            self._edges = self.graph.edges()
        return self._edges

    def is_cyclic(self):
        return bool(list(networkx.simple_cycles(self.graph)))

    def add_edge(self, from_node, to_node, attr_dict=None, **kwargs):
        self._invalidate_cache()
        self.graph.add_edge(from_node, to_node, attr_dict, **kwargs)

    def add_dep_edges_one_to_many(self, from_node, to_nodes):
        self._invalidate_cache()
        self.graph.add_edges_from(
            self.edge_attr(from_node, to_node) for to_node in to_nodes)

    def edge_attr(self, from_node, to_node):
        return from_node, to_node, {}

    deps_func = staticmethod(expression_dependencies)

    def _edges_recursive(self, out_vars):
        prev_nodes = self.nodes()
        if out_vars == self._root_node:
            # terminal node
            self.add_dep_edges_one_to_many(self._root_node, self.out_vars)
            deps = self.out_vars
        else:
            deps = []
            for var in out_vars:
                if is_numeral(var) or isinstance(var, InputVariable):
                    continue
                if isinstance(var, InputVariableTuple):
                    expr = var
                else:
                    expr = self.env[var]
                local_deps = self.deps_func(expr)
                deps += local_deps
                self.add_dep_edges_one_to_many(var, local_deps)
        if not deps:
            return
        new_deps = []
        for v in deps:
            if v not in prev_nodes:
                new_deps.append(v)
        self._edges_recursive(new_deps)

    def input_vars(self):
        return (v for v in self.nodes() if isinstance(v, InputVariable))

    def dfs_postorder(self):
        for node in networkx.dfs_postorder_nodes(self.graph, self._root_node):
            if node == self._root_node:
                continue
            yield node

    def is_multiply_shared(self, node):
        return len(self.predecessors(node)) > 1


class HierarchicalDependenceGraph(DependenceGraph):
    # FIXME broken
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
            if isinstance(each_node, HierarchicalDependenceGraph):
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
