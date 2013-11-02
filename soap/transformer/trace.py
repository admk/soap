"""
.. module:: soap.transformer.trace
    :synopsis: implementation of TraceExpr classes.
"""
import itertools

import soap.logger as logger
from soap.expression import Expression, expression_factory
from soap.transformer.martel import MartelTreeTransformer
from soap.transformer.utils import closure, greedy_frontier_closure
from soap.analysis import expr_frontier


class TraceExpr(Expression):
    """A subclass of :class:`soap.expression.Expression` for bottom-up
    hierarchical equivalence finding.

    Implements :member:`traces` that finds equivalnent expressions. Subclasses
    need to override :member:`closure`.
    """
    def traces(self, var_env=None, depth=None, prec=None, **kwargs):
        _, discovered = self._traces(var_env, depth, prec, **kwargs)
        return discovered

    def _traces(self, var_env=None, depth=None, prec=None, **kwargs):
        subtraces = []
        discovered = []
        for a in self.args:
            try:
                arg_subtraces, arg_discovered = \
                    self.__class__(*a)._traces(var_env, depth, prec, **kwargs)
            except (ValueError, TypeError):
                arg_subtraces = arg_discovered = {a}
            subtraces.append(arg_subtraces)
            discovered.append(arg_discovered)
        list_to_expr_set = lambda st: set(expression_factory(self.op, args)
                                          for args in itertools.product(*st))
        logger.debug('Generating traces')
        subtraces = list_to_expr_set(subtraces)
        logger.debug('Generated %d traces for tree: %s' %
                     (len(subtraces), str(self)))
        logger.debug('Finding closure')
        closure = set(self.closure(
            subtraces, depth=depth, var_env=var_env, prec=prec, **kwargs))
        return closure, closure | subtraces | list_to_expr_set(discovered)

    def clousure(self, trees, **kwargs):
        raise NotImplementedError

    def __repr__(self):
        return "TraceExpr(op='%s', a1=%s, a2=%s)" % \
            (self.op, repr(self.a1), repr(self.a2))


class MartelTraceExpr(TraceExpr):
    """A subclass of :class:`TraceExpr` to generate Martel's results."""
    def closure(self, trees, **kwargs):
        return MartelTreeTransformer(
            trees, depth=kwargs['depth']).closure()


class GreedyTraceExpr(TraceExpr):
    """A subclass of :class:`TraceExpr` to generate our greedy_trace equivalent
    expressions."""
    def closure(self, trees, **kwargs):
        return greedy_frontier_closure(trees, **kwargs)


class FrontierTraceExpr(TraceExpr):
    """A subclass of :class:`TraceExpr` to generate our frontier_trace
    equivalent expressions."""
    def closure(self, trees, **kwargs):
        return expr_frontier(closure(trees, depth=kwargs['depth']),
                             kwargs['var_env'], prec=kwargs['prec'])
