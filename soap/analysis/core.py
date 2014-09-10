"""
.. module:: soap.analysis.core
    :synopsis: Analysis classes.
"""
from collections import namedtuple

from soap import logger
from soap.common import Flyweight
from soap.context import context
from soap.semantics import error_eval, ErrorSemantics, inf, luts


def abs_error(expr, state):
    v = ErrorSemantics(error_eval(expr, state))
    if v.is_bottom():
        logger.error(
            'Cannot compute error for unreachable expression. '
            'Please run analysis on code to find unreachable statements.')
        return inf
    return float(max(abs(v.e.min), abs(v.e.max)))


def _pareto_frontier_2d(expr_set):
    if not expr_set:
        return expr_set, expr_set
    expr_set = sorted(expr_set)
    head, *tail = expr_set
    optimal = [head]
    suboptimal = []
    for m in tail:
        if m[1] < optimal[-1][1]:
            optimal.append(m)
        else:
            suboptimal.append(m)
    return optimal, suboptimal


def pareto_frontier_2d(expr_set):
    return _pareto_frontier_2d(expr_set)[0]


def thick_frontier_2d(expressions, keys=None):
    frontier = []
    for _ in range(context.thickness + 1):
        optimal, expressions = _pareto_frontier_2d(expressions)
        frontier += optimal
    return frontier


AnalysisResult = namedtuple('AnalysisResult', ['area', 'error', 'expression'])


class Analysis(Flyweight):

    def __init__(self, expr_set, state, out_vars=None):
        """Analysis class initialisation.

        :param expr_set: A set of expressions or a single expression.
        :type expr_set: `set` or :class:`soap.expression.Expression`
        :param state: The ranges of input variables.
        :type state: dictionary containing mappings from variables to
            :class:`soap.semantics.error.Interval`
        """
        super().__init__()
        self.expr_set = expr_set
        self.state = state
        self.out_vars = out_vars
        self._results = None

    def analyze(self):
        """Analyzes the set of expressions with input ranges and precisions
        provided in initialisation.

        :returns: a list of dictionaries each containing results and the
            expression.
        """
        results = self._results
        if results:
            return results

        state = self.state
        out_vars = self.out_vars
        precision = context.precision

        results = set()
        step = 0
        total = len(self.expr_set)
        for expr in self.expr_set:
            step += 1
            logger.persistent(
                'Analysing', '%d/%d' % (step, total), l=logger.levels.debug)
            area = luts(expr, state, out_vars, precision)
            error = abs_error(expr, state)
            results.add(AnalysisResult(area, error, expr))
        logger.unpersistent('Analysing')

        self._results = results
        return results

    def frontier(self):
        """Computes the Pareto frontier from analyzed results."""
        return pareto_frontier_2d(self.analyze())

    def thick_frontier(self):
        return thick_frontier_2d(self.analyze())
