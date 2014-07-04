"""
.. module:: soap.transformer.trace
    :synopsis: implementation of TraceExpr classes.
"""
import itertools

from soap import logger
from soap.analysis import expr_frontier
from soap.common import base_dispatcher
from soap.context import context as global_context
from soap.expression import expression_factory, SelectExpr, FixExpr
from soap.semantics.state import MetaState
from soap.semantics.state.fusion import fusion
from soap.semantics.functions import (
    arith_eval_meta_state, fixpoint_eval, expand_expr
)
from soap.transformer.arithmetic import MartelTreeTransformer
from soap.transformer.utils import closure, greedy_frontier_closure, reduce


class BaseDiscoverer(base_dispatcher('discover', 'discover')):
    """Bottom-up hierarchical equivalence finding.

    Subclasses need to override :member:`closure`.
    """
    def filter(self, expr_set, state, context):
        raise NotImplementedError

    def closure(self, expr_set, state, context):
        raise NotImplementedError

    def generic_discover(self, expr, state, context):
        raise TypeError(
            'Do not know how to discover equivalent expressions of {!r}'
            .format(expr))

    def _discover_atom(self, expr, state, context):
        return {expr}

    discover_numeral = _discover_atom
    discover_Variable = _discover_atom

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
    discover_BinaryBoolExpr = _discover_expression
    discover_SelectExpr = _discover_expression

    @staticmethod
    def _equivalent_loop_meta_states(expr, depth):
        unroll_state = loop_state = expr.loop_state
        expanded_bool_expr = expand_expr(expr.bool_expr, loop_state)

        yield unroll_state

        for d in range(depth):
            new_unroll_state = {}
            for var, expr in unroll_state.items():
                true_expr = expand_expr(expr, loop_state)
                false_expr = loop_state[var]
                if true_expr == false_expr:
                    new_unroll_state[var] = true_expr
                else:
                    expr = SelectExpr(
                        expanded_bool_expr, true_expr, false_expr)
                    new_unroll_state[var] = expr
            unroll_state = MetaState(new_unroll_state)
            yield unroll_state

    def discover_FixExpr(self, expr, state, context):
        bool_expr = expr.bool_expr
        loop_meta_state = expr.loop_state
        loop_var = expr.loop_var

        loop_meta_state_set = set(
            self._equivalent_loop_meta_states(expr, context.unroll_depth))

        init_meta_state_set = self.discover_MetaState(
            expr.init_state, state, context)

        eq_expr_set = set()

        # for each discovered init_meta_state values
        for init_meta_state in init_meta_state_set:
            # compute loop optimizing value ranges
            init_value_state = arith_eval_meta_state(init_meta_state, state)
            loop_value_state = fixpoint_eval(
                init_value_state, bool_expr, loop_meta_state)['entry']

            # transform bool_expr
            transformed_bool_expr_set = self._discover_expression(
                bool_expr, loop_value_state, context)

            # transform loop_meta_state
            for loop_meta_state in loop_meta_state_set:
                transformed_loop_meta_state_set = \
                    self.discover_MetaState(
                        loop_meta_state, loop_value_state, context)

                for transformed_bool_expr, transformed_loop_meta_state in \
                        itertools.product(
                            transformed_bool_expr_set,
                            transformed_loop_meta_state_set):
                    eq_expr = FixExpr(
                        transformed_bool_expr, transformed_loop_meta_state,
                        loop_var, init_meta_state)
                    eq_expr_set.add(eq_expr)

        return self.filter(eq_expr_set, state, context)

    def _discover_multiple_expressions(self, var_expr_state, state, context):
        var_list = list(var_expr_state.keys())
        eq_expr_list = [
            self(var_expr_state[var], state, context) for var in var_list]

        state_set = set()
        for expr_list in itertools.product(*eq_expr_list):
            eq_state = {var: expr for var, expr in zip(var_list, expr_list)}
            state_set.add(fusion(eq_state, out_vars))
        state_set = self.filter(state_set, state, context)

        return state_set

    discover_dict = _discover_multiple_expressions
    discover_MetaState = _discover_multiple_expressions

    def _execute(self, expr, state, context=None):
        context = context or global_context
        return super()._execute(expr, state, context)


class MartelDiscoverer(BaseDiscoverer):
    """A subclass of :class:`BaseDiscoverer` to generate Martel's results."""
    def filter(self, expr_set, state, context):
        return expr_set

    def closure(self, expr_set, state, context):
        transformer = MartelTreeTransformer(
            expr_set, depth=context.window_depth)
        return transformer.closure()


class GreedyDiscoverer(BaseDiscoverer):
    """
    A subclass of :class:`BaseDiscoverer` to generate our greedy_trace
    equivalent expressions.
    """
    def filter(self, expr_set, state, context):
        return expr_frontier(expr_set, state, prec=context.precision)

    def closure(self, expr_set, state, context):
        return greedy_frontier_closure(
            expr_set, state, depth=context.window_depth,
            prec=context.precision)


class FrontierDiscoverer(BaseDiscoverer):
    """A subclass of :class:`BaseDiscoverer` to generate our frontier_trace
    equivalent expressions."""
    def filter(self, expr_set, state, context):
        return expr_frontier(expr_set, state, prec=context.precision)

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