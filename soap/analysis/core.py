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


def _pareto_frontier(points):
    """Last row is always the expression!"""

    dom_func = lambda dominator_row, dominated_row: not any(
        dominator > dominated
        for dominator, dominated in zip(dominator_row, dominated_row))

    pareto_points = set()
    for candidate_row in points:
        candidate_stat = candidate_row[:-1]
        to_remove = set()
        for pareto_row in pareto_points:
            pareto_stat = pareto_row[:-1]
            if pareto_stat == candidate_stat:
                continue
            if dom_func(candidate_stat, pareto_stat):
                to_remove.add(pareto_row)
            if dom_func(pareto_stat, candidate_stat):
                break
        else:
            pareto_points.add(candidate_row)
        pareto_points -= to_remove

    dominated_points = set(points) - pareto_points
    return pareto_points, dominated_points


def pareto_frontier(points):
    return _pareto_frontier(points)[0]


def thick_frontier(points):
    frontier = []
    for _ in range(context.thickness + 1):
        optimal, points = _pareto_frontier(points)
        frontier += optimal
    return frontier


class AnalysisResult(
        namedtuple('AnalysisResult', ['area', 'error', 'expression'])):
    def __str__(self):
        return '({}, {}, {})'.format(*self)


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

        expr_set = self.expr_set
        state = self.state
        out_vars = self.out_vars
        precision = context.precision

        results = set()
        step = 0
        total = len(expr_set)
        try:
            for expr in expr_set:
                step += 1
                logger.persistent(
                    'Analysing', '{}/{}'.format(step, total),
                    l=logger.levels.debug)
                area = luts(expr, state, out_vars, precision)
                error = abs_error(expr, state)
                results.add(AnalysisResult(area, error, expr))
        except KeyboardInterrupt:
            logger.warning('Analysis interrupted.')
        logger.unpersistent('Analysing')

        self._results = results
        return results

    def frontier(self):
        """Computes the Pareto frontier from analyzed results."""
        return pareto_frontier(self.analyze())

    def thick_frontier(self):
        return thick_frontier(self.analyze())
