import collections

from soap.label import Label
from soap.expression import (
    is_variable, is_expression,
    Variable, InputVariable, External,
    VariableTuple, InputVariableTuple, OutputVariableTuple,
    FixExpr
)
from soap.semantics import is_numeral, MetaState, LabelSemantics


_LEAF = object()


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
    # DIRTY dummy leaf is to make sure it gets generated
    if isinstance(expr, External):
        # external dependencies taken care of by FixExpr dependencies.
        return [_LEAF]
    if expr == _LEAF:
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
        return [expr]
    if isinstance(expr, (dict, MetaState)):
        return [expr]
    if isinstance(expr, LabelSemantics):
        return [expr]
    raise TypeError(
        'Do not know how to find dependencies in expression {!r}'
        .format(expr))


def unique(bag_list):
    new_list = []
    for each in bag_list:
        if each not in new_list:
            new_list.append(each)
    return new_list


def sorted_vars(env, out_vars):
    # TODO.possible sorted dependent input variables, if do get a chance to
    # create determinism for graph dependency resolution, this may no longer be
    # necessary, because it can be replaced by a method in DependencyGraph
    def sort(env, out_vars):
        if isinstance(out_vars, InputVariable):
            return [Variable(out_vars.name)]
        if is_numeral(out_vars):
            return []

        is_seq = (isinstance(out_vars, collections.Sequence) and
                  not isinstance(out_vars, OutputVariableTuple))
        if not is_seq:
            out_vars = [out_vars]

        deps = []
        for var in out_vars:
            expr = env.get(var)
            for dep in expression_dependencies(expr):
                deps += sort(env, dep)
        return deps

    return unique(sort(env, out_vars))


class CyclicGraphException(Exception):
    pass


class DependencyGraph(object):
    """Discovers the graph of dependencies"""
    def __init__(self, env, out_var):
        super().__init__()
        env = dict(env)
        self._detect_acyclic(env, out_var)
        if isinstance(out_var, collections.Sequence):
            if not isinstance(out_var, VariableTuple):
                out_var = InputVariableTuple(out_var)
        self.env = dict(env)
        self.out_var = out_var
        self._edges = None
        self._nodes = None
        self._closure = None
        self._next_dict = None
        self._prev_dict = None
        self._dep_dict = None
        self._flow_dict = None

    @property
    def edges(self):
        def edges_recursive(var_set):
            edges = set()
            deps = set()
            for var in var_set:
                expr = self.env.get(var)
                local_deps = expression_dependencies(expr)
                deps |= set(local_deps)
                edges |= {(var, dep_var) for dep_var in local_deps}
            if deps:
                edges |= edges_recursive(deps)
            return edges

        edges = self._edges
        if edges:
            return edges
        out_vars = self.out_var
        if not isinstance(out_vars, InputVariableTuple):
            out_vars = [out_vars]
        self._edges = edges_recursive(out_vars)
        return self._edges

    @edges.setter
    def edges(self, edges):
        self._edges = edges
        self._nodes = None
        self._closure = None
        self._next_dict = None
        self._prev_dict = None
        self._dep_dict = None
        self._flow_dict = None

    @property
    def nodes(self):
        nodes = self._nodes
        if nodes:
            return nodes
        nodes = set()
        for x, y in self.edges:
            nodes |= {x, y}
        self._nodes = nodes
        return nodes

    @property
    def closure(self):
        closure = self._closure
        if closure:
            return closure
        closure = set(self.edges)
        while True:
            local_closure = set(closure)
            for start_var, mid_var in local_closure:
                if is_variable(mid_var):
                    continue
                for alt_mid_var, end_var in local_closure:
                    if mid_var != alt_mid_var:
                        continue
                    new_edge = (start_var, end_var)
                    if new_edge in closure:
                        continue
                    closure.add(new_edge)
            if local_closure == closure:
                break
        return closure

    @property
    def prev_dict(self):
        d = self._prev_dict
        if d:
            return d
        self._next_dict, self._prev_dict = self._generate_dictionaries(
            self.edges)
        return self.prev_dict

    @property
    def next_dict(self):
        d = self._next_dict
        if d:
            return d
        self._next_dict, self._prev_dict = self._generate_dictionaries(
            self.edges)
        return self._next_dict

    @property
    def dep_dict(self):
        d = self._dep_dict
        if d:
            return d
        self._dep_dict, self._flow_dict = self._generate_dictionaries(
            self.closure)
        return self._dep_dict

    @property
    def flow_dict(self):
        d = self._flow_dict
        if d:
            return d
        self._dep_dict, self._flow_dict = self._generate_dictionaries(
            self.closure)
        return self._flow_dict

    def prev(self, y):
        if isinstance(y, set):
            return set.union(*(self.prev(var) for var in y))
        return self.prev_dict.get(y, set())

    def next(self, x):
        if isinstance(x, set):
            return set.union(*(self.next(var) for var in x))
        return self.next_dict.get(x, set())

    def dataflows(self, y):
        return self.flow_dict.get(y, set())

    def dependencies(self, x):
        return self.dep_dict.get(x, set())

    def order_by_dependencies(self, variables):
        if not variables:
            return []
        variables = list(variables)
        for idx, var in enumerate(variables):
            if not (self.dependencies(var) & set(variables)):
                # independent on some other
                break
        unordered = variables[:idx] + variables[idx + 1:]
        return [var] + self.order_by_dependencies(unordered)

    def depends_on(self, x, y):
        return y in self.dep_dict.get(x, set())

    def is_multiply_shared(self, x):
        return len(self.prev(x)) > 1

    @staticmethod
    def _generate_dictionaries(edges):
        dep_dict = {}
        flow_dict = {}
        for var, dep_var in edges:
            deps = dep_dict.setdefault(var, set())
            deps.add(dep_var)
            flows = flow_dict.setdefault(dep_var, set())
            flows.add(var)
        return dep_dict, flow_dict

    @staticmethod
    def _detect_acyclic(env, out_var):
        def walk(var, found_vars):
            expr = env.get(var)
            dep_vars = expression_dependencies(expr)
            for dep_var in dep_vars:
                if dep_var in found_vars:
                    raise CyclicGraphException(
                        'Cycle detected: {}'.format(found_vars + [dep_var]))
                walk(dep_var, found_vars + [var])
        if not isinstance(out_var, VariableTuple):
            if not isinstance(out_var, collections.Sequence):
                out_var = [out_var]
        for var in out_var:
            walk(var, [])


class HierarchicalDependencyGraph(DependencyGraph):
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
                    subgraph = HierarchicalDependencyGraph(
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
