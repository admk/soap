"""
.. module:: soap.transformer.trace
    :synopsis: implementation of TraceExpr classes.
"""
import itertools

import soap.logger as logger
from soap.common import base_dispatcher
from soap.expression import expression_factory
from soap.transformer.martel import MartelTreeTransformer
from soap.transformer.utils import closure, greedy_frontier_closure, reduce
from soap.analysis import expr_frontier
from soap.context import context as global_context


class BaseDiscoverer(base_dispatcher('discover', 'discover')):
    """Bottom-up hierarchical equivalence finding.

    Subclasses need to override :member:`closure`.
    """
    def closure(self, expr_set, state, context):
        raise NotImplementedError

    def generic_discover(self, expr, state, context):
        raise TypeError(
            'Do not know how to discover equivalent expressions of {!r}'
            .format(expr))

    def _discover_atom(self, expr, state, context):
        return {expr}

    def _discover_expression(self, expr, state, context):
        op = expr.op
        eq_args_list = tuple(self(arg, state, context) for arg in expr.args)
        expr_set = {
            expression_factory(op, *args)
            for args in itertools.product(*eq_args_list)
        }
        expr_set = self.closure(expr_set, state, context)
        logger.debug(
            'Discover: {}, Equivalent: {}'.format(expr, len(expr_set)))
        return expr_set

    discover_BinaryArithExpr = _discover_expression
    discover_SelectExpr = _discover_expression
    discover_numeral = _discover_atom
    discover_Variable = _discover_atom

    def _execute(self, expr, state, context=None):
        context = context or global_context
        return super()._execute(expr, state, context)


class MartelDiscoverer(BaseDiscoverer):
    """A subclass of :class:`BaseDiscoverer` to generate Martel's results."""
    def closure(self, expr_set, state, context):
        transformer = MartelTreeTransformer(
            expr_set, depth=context.window_depth)
        return transformer.closure()


class GreedyDiscoverer(BaseDiscoverer):
    """
    A subclass of :class:`BaseDiscoverer` to generate our greedy_trace
    equivalent expressions.
    """
    def closure(self, expr_set, state, context):
        return greedy_frontier_closure(
            expr_set, state, depth=context.window_depth,
            prec=context.precision)


class FrontierDiscoverer(BaseDiscoverer):
    """A subclass of :class:`BaseDiscoverer` to generate our frontier_trace
    equivalent expressions."""
    def closure(self, expr_set, state, context):
        expr_set = closure(expr_set, depth=context.window_depth)
        return expr_frontier(expr_set, state, prec=context.precision)


def _discover(discoverer_class, expr, state, context):
    expr_set = discoverer_class()(expr, state, context)
    return reduce(expr_set)


def greedy(expr, state, context=None):
    """Finds our equivalent expressions using :class:`GreedyDiscoverer`.

    :param expr: The original expression.
    :type expr: :class:`soap.expression.Expression`
    :param state: The ranges of input variables.
    :type state: :class:`soap.semantics.state.BoxState`
    :param context: The global context used for evaluation
    :type context: :class:`soap.context.soap.SoapContext`
    """
    return _discover(GreedyDiscoverer, expr, state, context)


def frontier(expr, state, context=None):
    """Finds our equivalent expressions using :class:`FrontierDiscoverer`.

    :param expr: The original expression.
    :type expr: :class:`soap.expression.Expression`
    :param state: The ranges of input variables.
    :type state: :class:`soap.semantics.state.BoxState`
    :param context: The global context used for evaluation
    :type context: :class:`soap.context.soap.SoapContext`
    """
    return _discover(FrontierDiscoverer, expr, state, context)


def martel(expr, state, context=None):
    """Finds Martel's equivalent expressions.

    :param expr: The original expression.
    :type expr: :class:`soap.expression.Expression`
    :param state: The ranges of input variables.
    :type state: :class:`soap.semantics.state.BoxState`
    :param context: The global context used for evaluation
    :type context: :class:`soap.context.soap.SoapContext`
    """
    return _discover(MartelDiscoverer, expr, state, context)
