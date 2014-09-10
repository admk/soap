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
from soap.expression import expression_factory, SelectExpr, FixExpr
from soap.program import Flow
from soap.semantics.state import BoxState, MetaState
from soap.semantics.functions import (
    arith_eval_meta_state, fixpoint_eval, expand_expr
)
from soap.transformer.arithmetic import MartelTreeTransformer
from soap.transformer.utils import (
    closure, greedy_frontier_closure, thick_frontier_closure
)


class BaseDiscoverer(base_dispatcher('discover')):
    """Bottom-up hierarchical equivalence finding.

    Subclasses need to override :member:`closure`.
    """
    def filter(self, expr_set, state, out_vars):
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
        frontier = self.closure(frontier_expr_set, state, out_vars)
        logger.debug('Discover: {}, Frontier: {}'.format(expr, len(frontier)))
        return frontier

    discover_UnaryArithExpr = discover_BinaryArithExpr = _discover_expression
    discover_UnaryBoolExpr = discover_BinaryBoolExpr = _discover_expression
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

    def discover_FixExpr(self, expr, state, out_vars):
        bool_expr = expr.bool_expr
        init_meta_state = expr.init_state
        loop_meta_state = expr.loop_state
        loop_var = expr.loop_var

        loop_meta_state_set = set(
            self._equivalent_loop_meta_states(expr, context.unroll_depth))

        frontier_init_meta_state_set = self(init_meta_state, state, [loop_var])

        logger.debug('Discover: {}, Frontier: {}'.format(
            init_meta_state, len(frontier_init_meta_state_set)))

        # compute loop optimizing value ranges
        init_value_state = arith_eval_meta_state(init_meta_state, state)
        loop_value_state = fixpoint_eval(
            init_value_state, bool_expr, loop_meta_state)['entry']

        # transform bool_expr
        frontier_bool_expr_set = self(bool_expr, loop_value_state, None)

        frontier_expr_set = set()
        i, n = 0, len(loop_meta_state_set)

        # transform loop_meta_state
        for loop_meta_state in loop_meta_state_set:
            i += 1
            logger.persistent('Unroll', '{}/{}'.format(i, n))

            frontier_loop_meta_state_set = self(
                loop_meta_state, loop_value_state, [loop_var])

            iterer = itertools.product(
                frontier_bool_expr_set, frontier_loop_meta_state_set,
                frontier_init_meta_state_set)
            for bool_expr, loop_meta_state, init_meta_state in iterer:
                fix_expr = FixExpr(
                    bool_expr, loop_meta_state, loop_var, init_meta_state)
                frontier_expr_set.add(fix_expr)

        logger.unpersistent('LoopTr')

        frontier = self.filter(frontier_expr_set, state, out_vars)

        logger.debug('Discover: {}, Frontier: {}'.format(expr, len(frontier)))

        return frontier

    def _discover_multiple_expressions(
            self, var_expr_state, state, out_vars):
        var_list = list(var_expr_state.keys())
        frontier_expr_list = [
            self(var_expr_state[var], state, out_vars) for var in var_list]

        frontier = set()
        for expr_list in itertools.product(*frontier_expr_list):
            eq_state = {var: expr for var, expr in zip(var_list, expr_list)}
            frontier.add(MetaState(eq_state))
        frontier = self.filter(frontier, state, out_vars)

        return frontier

    discover_dict = _discover_multiple_expressions
    discover_MetaState = _discover_multiple_expressions

    @cached
    def __call__(self, expr, state, out_vars=None):
        return super().__call__(expr, state, out_vars)


class MartelDiscoverer(BaseDiscoverer):
    """A subclass of :class:`BaseDiscoverer` to generate Martel's results."""
    def filter(self, expr_set, state, out_vars):
        return expr_set

    def closure(self, expr_set, state, out_vars):
        transformer = MartelTreeTransformer(
            expr_set, depth=context.window_depth)
        return transformer.closure()


class _FrontierFilter(BaseDiscoverer):
    def filter(self, expr_set, state, out_vars):
        return [
            r.expression for r in analysis_frontier(expr_set, state, out_vars)]


class GreedyDiscoverer(_FrontierFilter):
    """
    A subclass of :class:`BaseDiscoverer` to generate our greedy_trace
    equivalent expressions.
    """
    def closure(self, expr_set, state, out_vars):
        return greedy_frontier_closure(expr_set, state, out_vars)


class ThickDiscoverer(BaseDiscoverer):
    def filter(self, expr_set, state, out_vars):
        return [r.expression
                for r in thick_analysis_frontier(expr_set, state, out_vars)]

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
