import functools
import itertools
import math

import islpy
import networkx
import numpy

from soap.context import context
from soap.datatype import ArrayType, int_type, real_type
from soap.expression import (
    AccessExpr, expression_factory, InputVariable, is_expression,
    is_variable, operators, UpdateExpr, Variable,
)
from soap.program.graph import DependenceGraph
from soap.semantics import is_numeral, IntegerInterval, Label, arith_eval
from soap.semantics.error import inf
from soap.semantics.functions import expand_expr


def max_latency(graph):
    dist = {}
    nodes = networkx.topological_sort(graph)
    for to_node in nodes:
        pred_dists = [
            dist[from_node] + graph[from_node][to_node]['latency']
            for from_node in graph.pred[to_node]]
        dist[to_node] = max([0] + pred_dists)
    return max(dist.values())


def rec_init_int_search(graph, init_ii=1, prec=None):
    """
    Performs a binary search of the recurrence-based minimum initiation
    interval (RecMII).
    """
    if not prec:
        prec = context.ii_precision
    inf = float('inf')
    neg_inf = -inf
    nodes = list(graph.nodes())
    len_nodes = len(nodes)
    dist_shape = [len_nodes] * 2

    def rec_init_int_check(ii):
        """
        Checks if the target II is valid.  Runs a modified Floyd-Warshall
        algorithm to test the absence of positive cycles.

        Input ii must be greater or equal to 1.
        """
        dist = numpy.full(dist_shape, neg_inf)
        iterer = itertools.product(enumerate(nodes), repeat=2)
        for (from_idx, from_node), (to_idx, to_node) in iterer:
            try:
                edge = graph[from_node][to_node]
            except KeyError:
                continue
            dist[from_idx, to_idx] = edge['latency'] - ii * edge['distance']

        iterer = itertools.product(range(len_nodes), repeat=3)
        for mid_idx, from_idx, to_idx in iterer:
            dist_val = dist[from_idx, mid_idx] + dist[mid_idx, to_idx]
            if dist_val > dist[from_idx, to_idx]:
                if from_idx == to_idx and dist_val > 0:
                    return False
                dist[from_idx, to_idx] = dist_val

        return True

    min_ii = max_ii = init_ii
    incr = prec = 2 ** -prec

    # find an upper-bound on MII
    while not rec_init_int_check(max_ii):
        max_ii += incr
        incr *= 2

    # binary search for the optimal MII
    last_ii = max_ii
    while max_ii - min_ii > prec:
        mid_ii = (min_ii + max_ii) / 2
        if rec_init_int_check(mid_ii):
            max_ii = last_ii = mid_ii
        else:
            min_ii = mid_ii

    return last_ii


def _rename_var_in_expr(expr, var_list, format_str):
    if is_variable(expr):
        if expr in var_list:
            return Variable(format_str.format(expr.name), dtype=expr.dtype)
        return expr
    if is_expression(expr):
        args = (_rename_var_in_expr(a, var_list, format_str)
                for a in expr.args)
        return expression_factory(expr.op, *args)
    return expr


class ISLExpressionError(Exception):
    """Expression is mal-formed.  """


class ISLIndependenceException(Exception):
    """No dependence.  """


def _stitch_expr(expr, env):
    if is_expression(expr):
        args = (_stitch_expr(a, env) for a in expr.args)
        return expression_factory(expr.op, *args)
    if isinstance(expr, Label):
        return _stitch_expr(env[expr], env)
    if is_numeral:
        return expr
    if isinstance(expr, InputVariable):
        return Variable(expr.name, expr.dtype)
    raise TypeError('Do not know how to stitch expression {}.'.format(expr))


def _stitch_env(env):
    mapping = {
        v: _stitch_expr(e, env) for v, e in env.items() if is_variable(v)
    }
    return env.__class__(mapping)


def _check_isl_expr(expr):
    variables = expr.vars()
    try:
        islpy.Set('{{ [{vars}]: {expr} > 0 }}'.format(
            vars=', '.join(v.name for v in variables), expr=expr))
    except islpy.Error:
        raise ISLExpressionError(
            'Expression {} is written in a format not expected by ISL.'
            .format(expr))


def dependence_vector(iter_vars, iter_slices, invariant, source, sink):
    """
    Uses ISL for dependence testing and returns the dependence vector.

    iter_vars: Iteration variables
    iter_slices: Iteration starts, stops and steps; stop is inclusive!
    loop_state: Loop invariant
    source, sink: Subscript objects
    """
    if len(source.args) != len(sink.args):
        raise ValueError('Source/sink subscript length mismatch.')

    dist_vars = []
    constraints = []
    exists_vars = set()
    for var, iter_slice in zip(iter_vars, iter_slices):
        dist_var = '__dist_{}'.format(var.name)
        dist_vars.append(dist_var)

        lower, upper = iter_slice.start, iter_slice.stop
        constraints.append(
            '{dist_var} = __snk_{iter_var} - __src_{iter_var}'
            .format(dist_var=dist_var, iter_var=var))
        constraints.append(
            '{lower} <= __src_{iter_var} < __snk_{iter_var} <= {upper}'
            .format(
                iter_var=var, lower=iter_slice.start, upper=iter_slice.stop))

        step = iter_slice.step
        if step <= 0:
            raise ValueError('For now we only deal with positive step size.')
        if step == 1:
            continue
        for node_type in ['src', 'snk']:
            exists_vars.add('__stride_{}_{}'.format(node_type, var))
            constraints.append(
                '__stride_{node_type}_{iter_var} * {step_size} = '
                '__{node_type}_{iter_var}'.format(
                    node_type=node_type, iter_var=var, step_size=step))

    for src_idx, snk_idx in zip(source.args, sink.args):
        _check_isl_expr(src_idx)
        _check_isl_expr(snk_idx)
        src_idx = _rename_var_in_expr(src_idx, iter_vars, '__src_{}')
        snk_idx = _rename_var_in_expr(snk_idx, iter_vars, '__snk_{}')
        constraints.append('{} = {}'.format(src_idx, snk_idx))
        exists_vars |= src_idx.vars() | snk_idx.vars()

    for var in exists_vars:
        if var.name.startswith('__'):
            continue
        lower, upper = invariant[var]
        if lower != -inf:
            constraints.append('{lower} <= {var}'.format(lower=lower, var=var))
        if upper != inf:
            constraints.append('{var} <= {upper}'.format(upper=upper, var=var))

    problem = '{{ [{dist_vars}] : exists ( {exists_vars} : {constraints} ) }}'
    problem = problem.format(
        dist_vars=', '.join(reversed(dist_vars)),
        iter_vars=', '.join(v.name for v in iter_vars),
        constraints=' and '.join(constraints),
        exists_vars=', '.join(v.name for v in exists_vars))

    basic_set = islpy.BasicSet(problem)
    dist_vect_list = []
    basic_set.lexmin().foreach_point(dist_vect_list.append)
    if not dist_vect_list:
        raise ISLIndependenceException
    if len(dist_vect_list) != 1:
        raise ValueError(
            'The function lexmin() should return a single point.')
    raw_dist_vect = dist_vect_list.pop()
    dist_vect = []
    for i in range(len(dist_vars)):
        val = raw_dist_vect.get_coordinate_val(islpy.dim_type.set, i)
        dist_vect.append(val.to_python())
    return tuple(reversed(dist_vect))


def _iter_point_count(iter_slice, minimize):
    bound = iter_slice.stop - iter_slice.start
    if isinstance(bound, IntegerInterval):
        if minimize:
            bound = bound.min
        else:
            bound = bound.max
    return max(0, int(math.floor(bound / iter_slice.step))) + 1


def dependence_distance(dist_vect, iter_slices):
    shape_prod = 1
    dist_sum = 0
    for dist, iter_slice in zip(reversed(dist_vect), reversed(iter_slices)):
        dist_sum += shape_prod * dist
        shape_prod *= _iter_point_count(iter_slice, minimize=True)
    return dist_sum


class DependenceType(object):
    independent = 0
    flow = 1
    anti = 2
    output = 3


class SequentialLatencyDependenceGraph(DependenceGraph):

    latency_table = {
        (int_type, operators.LESS_OP): 1,
        (int_type, operators.ADD_OP): 1,
        (real_type, operators.ADD_OP): 7,
        (real_type, operators.INDEX_ACCESS_OP): 2,
        (int_type, operators.INDEX_ACCESS_OP): 2,
        (ArrayType, operators.INDEX_UPDATE_OP): 1,
        (None, operators.SUBSCRIPT_OP): 0,
    }

    def __init__(self, env, state, out_vars):
        self.state = state
        super().__init__(env, out_vars)

    def _node_latency(self, node):
        if isinstance(node, InputVariable):
            return 0
        if is_numeral(node):
            return 0
        expr = self.env[node]
        if is_expression(expr):
            dtype = node.dtype
            if isinstance(dtype, ArrayType):
                dtype = ArrayType
            if expr.op != operators.FIXPOINT_OP:
                return self.latency_table[dtype, expr.op]
            # FixExpr
            for_loop = _extract_for_loop(expr)
            graph = LoopLatencyDependenceGraph(
                expr.loop_state, [expr.loop_var], [for_loop['iter_var']],
                [for_loop['iter_slice']], for_loop['invariant'])
            return graph.latency()
        if is_numeral(expr) or isinstance(expr, (Label, Variable)):
            return 0
        raise TypeError(
            'Do not know how to compute latency for node {}'.format(node))

    def edge_attr(self, from_node, to_node):
        attr_dict = {
            'type': DependenceType.flow,
            'latency': self._node_latency(to_node),
            'distance': 0,
        }
        return from_node, to_node, attr_dict

    def latency(self):
        try:
            return self._latency
        except AttributeError:
            self._latency = max_latency(self.graph)
            return self._latency


class LoopNestExtractionFailureException(Exception):
    """Failed to extract loop nest.  """


class ForLoopExtractionFailureException(Exception):
    """Failed to extract for loop.  """


def _extract_for_loop(fix_expr):
    bool_expr, loop_state, loop_var, init_state = fix_expr.args

    label, env = bool_expr
    bool_expr = _stitch_expr(label, env)

    invariant = loop_state['__invariant']
    loop_state = _stitch_env(loop_state)

    iter_var, stop = bool_expr.args
    if not is_variable(iter_var):
        raise ForLoopExtractionFailureException

    if bool_expr.op not in [operators.LESS_OP, operators.LESS_EQUAL_OP]:
        raise ForLoopExtractionFailureException

    # make sure stop_expr value is not changed throughout loop iterations
    if stop != expand_expr(stop, loop_state):
        raise ForLoopExtractionFailureException

    step_expr = loop_state[iter_var]
    if step_expr.op != operators.ADD_OP:
        raise ForLoopExtractionFailureException
    arg_1, arg_2 = step_expr.args
    if arg_1 == iter_var:
        step = arg_2
    elif arg_2 == iter_var:
        step = arg_1
    else:
        raise ForLoopExtractionFailureException

    start = invariant[iter_var].min
    stop = invariant[iter_var].max
    step = arith_eval(step, invariant)
    if step.min != step.max:
        raise ForLoopExtractionFailureException
    step = step.min

    for_loop = {
        'iter_var': iter_var,
        'iter_slice': slice(start, stop, step),
        'loop_var': loop_var,
        'invariant': invariant,
    }
    return for_loop


class LoopLatencyDependenceGraph(SequentialLatencyDependenceGraph):
    def __init__(self, env, out_vars, iter_vars, iter_slices, invariant):
        super().__init__(env, invariant, out_vars)
        self.iter_vars = iter_vars
        self.iter_slices = iter_slices
        self.invariant = invariant
        self._init_loop_graph(self.graph)

    def _init_loop_graph(self, graph):
        loop_graph = graph.copy()
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
        # we do it for flow dependence only WAR and WAW are not true
        # dependences, as read/write accesses can always be performed
        # consecutively.
        from_expr = _stitch_expr(from_node, self.env)
        to_expr = _stitch_expr(to_node, self.env)
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
        try:
            dist_vect = dependence_vector(
                self.iter_vars, self.iter_slices, self.invariant,
                source_expr, sink_expr)
        except ISLIndependenceException:
            return
        distance = dependence_distance(dist_vect, self.iter_slices)

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
            self._initiation_interval = rec_init_int_search(self.loop_graph)
            return self._initiation_interval

    def depth(self):
        try:
            return self._depth
        except AttributeError:
            self._depth = max_latency(self.graph)
            return self._depth

    def trip_count(self):
        trip_counts = [_iter_point_count(s, False) for s in self.iter_slices]
        return functools.reduce(lambda x, y: x * y, trip_counts)

    def latency(self):
        try:
            return self._latency
        except AttributeError:
            pass
        ii = self.initiation_interval()
        self._latency = (self.trip_count() - 1) * ii + self.depth()
        return self._latency

    def true_latency(self):
        ii = math.ceil(self.initiation_interval())
        return (self.trip_count() - 1) * ii + self.depth()


def latency_eval(expr, state, out_vars=None):
    from soap.semantics import BoxState, label
    if not state:
        state = BoxState(bottom=True)
    label, env = label(expr, state, out_vars)
    if is_expression(expr):
        # expressions do not have out_vars, but have an output, in this case
        # ``label`` is its output variable
        out_vars = [label]
    graph = SequentialLatencyDependenceGraph(env, state, out_vars)
    return graph.latency()
