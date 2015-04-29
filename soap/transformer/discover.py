"""
.. module:: soap.transformer.trace
    :synopsis: implementation of TraceExpr classes.
"""
import collections
import itertools

from soap import logger
from soap.analysis import (
    frontier as analysis_frontier, thick_frontier as thick_analysis_frontier
)
from soap.common import base_dispatcher, cached
from soap.context import context
from soap.expression import (
    expression_factory, SelectExpr, FixExpr, operators, UnrollExpr
)
from soap.program import Flow
from soap.semantics import BoxState, ErrorSemantics, MetaState
from soap.semantics.functions import (
    arith_eval_meta_state, unroll_fix_expr, fixpoint_eval,
)
from soap.semantics.functions.label import _label
from soap.transformer.arithmetic import MartelTreeTransformer
from soap.transformer.utils import (
    closure, greedy_frontier_closure, thick_frontier_closure
)


class Unroller(base_dispatcher('unroll')):
    def generic_unroll(self, expr):
        raise TypeError('Do not know how to unroll {!r}'.format(expr))

    def _unroll_atom(self, expr):
        return expr

    unroll_numeral = _unroll_atom
    unroll_Variable = _unroll_atom

    def _unroll_expression(self, expr):
        return expression_factory(expr.op, *[self(arg) for arg in expr.args])

    unroll_UnaryArithExpr = unroll_BinaryArithExpr = _unroll_expression
    unroll_UnaryBoolExpr = unroll_BinaryBoolExpr = _unroll_expression
    unroll_Subscript = unroll_AccessExpr = _unroll_expression
    unroll_SelectExpr = unroll_UpdateExpr = _unroll_expression

    def unroll_FixExpr(self, expr):
        init_state = self(expr.init_state)
        loop_state = self(expr.loop_state)
        fix_expr = FixExpr(
            expr.bool_expr, loop_state, expr.loop_var, init_state)
        return UnrollExpr(fix_expr, loop_state, context.unroll_depth)

    def unroll_MetaState(self, expr):
        return MetaState({v: self(e) for v, e in expr.items()})


unroll = Unroller()


class BaseDiscoverer(base_dispatcher('discover')):
    """Bottom-up hierarchical equivalence finding.

    Subclasses need to override :member:`closure`.
    """
    def filter(self, expr_set, state, out_vars, **kwargs):
        raise NotImplementedError

    def closure(self, expr_set, state, out_vars):
        raise NotImplementedError

    def generic_discover(self, expr, state, out_vars):
        raise TypeError(
            'Do not know how to discover equivalent expressions of {!r}'
            .format(expr))

    def _discover_atom(self, expr, state, out_vars):
        return {expr}

    discover_numeral = _discover_atom
    discover_Variable = _discover_atom

    def _discover_expression(self, expr, state, out_vars):
        op = expr.op
        frontier_args_list = [self(arg, state, out_vars) for arg in expr.args]
        frontier_expr_set = {
            expression_factory(op, *args)
            for args in itertools.product(*frontier_args_list)
        }
        frontier_expr_set.add(expr)
        logger.info('Discovering: {}'.format(expr))
        frontier = self.closure(frontier_expr_set, state, out_vars)
        logger.info('Discovered: {}, Frontier: {}'.format(expr, len(frontier)))
        return frontier

    discover_UnaryArithExpr = discover_BinaryArithExpr = _discover_expression
    discover_UnaryBoolExpr = discover_BinaryBoolExpr = _discover_expression

    def discover_SelectExpr(self, expr, state, out_vars):
        bool_expr, true_expr, false_expr = expr.args
        bool_expr_set = self(bool_expr, state, out_vars)
        true_expr_set = self(true_expr, state, out_vars)
        false_expr_set = self(false_expr, state, out_vars)

        logger.info('Discovering: {}, {}'.format(true_expr, false_expr))

        iterer = itertools.product(true_expr_set, false_expr_set)
        true_false_set = set()
        for each_true_expr, each_false_expr in iterer:
            true_false_set.add(expression_factory(
                operators.BARRIER_OP, each_true_expr, each_false_expr))
        true_false_set = self.filter(true_false_set, state, out_vars)

        logger.info('Discovered: {}, {}, Frontier: {}'.format(
            true_expr, false_expr, len(true_false_set)))

        iterer = itertools.product(bool_expr_set, true_false_set)
        expr_set = set()
        for bool_expr, true_false_expr in iterer:
            true_expr, false_expr = true_false_expr.args
            expr_set.add(SelectExpr(bool_expr, true_expr, false_expr))

        expr_set = self.filter(expr_set, state, out_vars)
        return self.closure(expr_set, state, out_vars)

    discover_AccessExpr = discover_UpdateExpr = _discover_expression
    discover_Subscript = _discover_expression

    def discover_FixExpr(self, expr, state, out_vars):
        bool_expr = expr.bool_expr
        init_meta_state = expr.init_state
        loop_meta_state = expr.loop_state
        loop_var = expr.loop_var

        logger.info('Discovering: {}'.format(init_meta_state))

        frontier_init_meta_state_set = self(init_meta_state, state, [loop_var])

        logger.info('Discovered: {}, Frontier: {}'.format(
            init_meta_state, len(frontier_init_meta_state_set)))

        # compute loop optimizing value ranges
        init_value_state = arith_eval_meta_state(init_meta_state, state)
        loop_value_state = fixpoint_eval(
            init_value_state, bool_expr, loop_meta_state)['entry']
        # set all errors to null to optimize loop specifically
        null_error_state = {}
        for var, error in loop_value_state.items():
            if isinstance(error, ErrorSemantics):
                error = ErrorSemantics(error.v, [0, 0])
            null_error_state[var] = error
        loop_value_state = state.__class__(null_error_state)

        logger.info('Discovering loop: {}'.format(loop_meta_state))

        fix_expr_list = list(unroll_fix_expr(
            expr, init_value_state, context.unroll_depth))
        frontier = {expr}
        total = len(fix_expr_list)

        for depth, fix_expr in enumerate(fix_expr_list):
            logger.persistent('Unroll', '{}/{}'.format(depth, total - 1))

            bool_expr = fix_expr.bool_expr

            frontier_loop_meta_state_set = self(
                fix_expr.loop_state, loop_value_state, [loop_var])

            iterer = itertools.product(
                frontier_loop_meta_state_set, frontier_init_meta_state_set)
            each_frontier = set()
            for each_loop_state, each_init_state in iterer:
                fix_expr = FixExpr(
                    bool_expr, each_loop_state, loop_var, each_init_state)
                each_frontier.add(fix_expr)

            each_frontier = set(self.filter(
                each_frontier, state, out_vars,
                size_limit=context.loop_size_limit))
            frontier |= each_frontier

        logger.unpersistent('Unroll')

        frontier = self.filter(frontier, state, out_vars, size_limit=0)

        logger.info('Discovered: {}, Frontier: {}'.format(expr, len(frontier)))

        return frontier

    def _discover_multiple_expressions(
            self, var_expr_state, state, out_vars):

        _, env = _label(var_expr_state, state)
        var_list = sorted(set(var_expr_state.keys()) | set(out_vars), key=hash)

        logger.info('Discovering state: {}'.format(var_expr_state))

        frontier = [{}]
        n = len(var_list)
        for i, var in enumerate(var_list):
            i += 1
            logger.persistent('Merge', '{}/{}'.format(i, n))
            var_expr_set = self(var_expr_state[var], state, out_vars)
            iterer = itertools.product(frontier, var_expr_set)
            new_frontier = []
            for meta_state, var_expr in iterer:
                meta_state = dict(meta_state)
                meta_state[var] = var_expr
                new_frontier.append(MetaState(meta_state))
            frontier = self.filter(new_frontier, state, var_list[:i])
        frontier = self.filter(frontier, state, out_vars)

        logger.unpersistent('Merge')
        logger.info('Discovered: {}, Frontier: {}'
                    .format(var_expr_state, len(frontier)))
        return frontier

    discover_dict = discover_MetaState = _discover_multiple_expressions

    @cached
    def __call__(self, expr, state, out_vars=None):
        return super().__call__(expr, state, out_vars)


class MartelDiscoverer(BaseDiscoverer):
    """A subclass of :class:`BaseDiscoverer` to generate Martel's results."""
    def filter(self, expr_set, state, out_vars, **kwargs):
        return expr_set

    def closure(self, expr_set, state, out_vars):
        transformer = MartelTreeTransformer(
            expr_set, depth=context.window_depth)
        return transformer.closure()


class _FrontierFilter(BaseDiscoverer):
    def filter(self, expr_set, state, out_vars, **kwargs):
        frontier = [
            r.expression for r in analysis_frontier(
                expr_set, state, out_vars, **kwargs)]
        return frontier


class GreedyDiscoverer(_FrontierFilter):
    """
    A subclass of :class:`BaseDiscoverer` to generate our greedy_trace
    equivalent expressions.
    """
    def closure(self, expr_set, state, out_vars):
        return greedy_frontier_closure(expr_set, state, out_vars)


class ThickDiscoverer(BaseDiscoverer):
    def filter(self, expr_set, state, out_vars, **kwargs):
        frontier = [
            r.expression for r in thick_analysis_frontier(
                expr_set, state, out_vars, **kwargs)]
        return frontier

    def closure(self, expr_set, state, out_vars):
        return thick_frontier_closure(expr_set, state, out_vars)


class FrontierDiscoverer(_FrontierFilter):
    """A subclass of :class:`BaseDiscoverer` to generate our frontier_trace
    equivalent expressions."""
    def closure(self, expr_set, state, out_vars):
        expr_set = closure(expr_set, depth=context.window_depth)
        return self.filter(expr_set, state, out_vars)


def _discover(discoverer, expr, state, out_vars):
    if isinstance(expr, Flow):
        state = state or expr.inputs()
        out_vars = out_vars or expr.outputs()

    if isinstance(expr, MetaState) and not out_vars:
        logger.warning(
            'Expect out_vars to be provided, using env.keys() instead')
        out_vars = expr.keys()
    if not isinstance(out_vars, collections.Sequence):
        logger.warning('Expect out_vars to be a sequence, will sort it')
        out_vars = sorted(out_vars, key=hash)
    if isinstance(expr, MetaState):
        expr = MetaState({k: v for k, v in expr.items() if k in out_vars})

    if not isinstance(state, BoxState):
        state = BoxState(state)

    return discoverer(expr, state, out_vars)


_martel_discoverer = MartelDiscoverer()
_greedy_discoverer = GreedyDiscoverer()
_frontier_discoverer = FrontierDiscoverer()
_thick_discoverer = ThickDiscoverer()


def thick(expr, state=None, out_vars=None):
    """Finds our equivalent expressions using :class:`ThickDiscoverer`.

    :param expr: An expression or a variable-expression mapping
    :type expr:
        :class:`soap.expression.Expression` or
        :class:`soap.semantics.state.MetaState`
    :param state: The ranges of input variables.
    :type state: :class:`soap.semantics.state.BoxState`
    :param out_vars: The output variables of the metastate
    :type out_vars: :class:`collections.Sequence`
    """
    return _discover(_thick_discoverer, expr, state, out_vars)


def greedy(expr, state=None, out_vars=None):
    """Finds our equivalent expressions using :class:`GreedyDiscoverer`.

    :param expr: An expression or a variable-expression mapping
    :type expr:
        :class:`soap.expression.Expression` or
        :class:`soap.semantics.state.MetaState`
    :param state: The ranges of input variables.
    :type state: :class:`soap.semantics.state.BoxState`
    :param out_vars: The output variables of the metastate
    :type out_vars: :class:`collections.Sequence`
    """
    return _discover(_greedy_discoverer, expr, state, out_vars)


def frontier(expr, state=None, out_vars=None):
    """Finds our equivalent expressions using :class:`FrontierDiscoverer`.

    :param expr: An expression or a variable-expression mapping
    :type expr:
        :class:`soap.expression.Expression` or
        :class:`soap.semantics.state.MetaState`
    :param state: The ranges of input variables.
    :type state: :class:`soap.semantics.state.BoxState`
    :param out_vars: The output variables of the metastate
    :type out_vars: :class:`collections.Sequence`
    """
    return _discover(_frontier_discoverer, expr, state, out_vars)


def martel(expr, state=None, out_vars=None):
    """Finds Martel's equivalent expressions.

    :param expr: An expression or a variable-expression mapping
    :type expr:
        :class:`soap.expression.Expression` or
        :class:`soap.semantics.state.MetaState`
    :param state: The ranges of input variables.
    :type state: :class:`soap.semantics.state.BoxState`
    :param out_vars: The output variables of the metastate
    :type out_vars: :class:`collections.Sequence`
    """
    return _discover(_martel_discoverer, expr, state, out_vars)
