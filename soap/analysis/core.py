"""
.. module:: soap.analysis.core
    :synopsis: Analysis classes.
"""
import collections
import random

from soap import logger
from soap.common import Flyweight
from soap.context import context
from soap.semantics import error_eval, ErrorSemantics, inf, schedule_graph


def abs_error(expr, state):
    v = ErrorSemantics(error_eval(expr, state))
    if v.is_bottom():
        logger.error(
            'Cannot compute error for unreachable expression. '
            'Please run analysis on code to find unreachable statements.')
        return inf
    return float(max(abs(v.e.min), abs(v.e.max)))


_analysis_result_tuple = collections.namedtuple(
    'AnalysisResult', ['lut', 'dsp', 'error', 'latency', 'expression'])


class AnalysisResult(_analysis_result_tuple):
    def stats(self):
        return self.lut, self.dsp, self.error, self.latency

    def format(self):
        return '({}, {}, {}, {}, {})'.format(
            self.lut, self.dsp, self.error, self.latency,
            self.expression.format())

    __str__ = format


def _pareto_frontier(points, ignore_last=True):
    # Last row can be an expression
    dom_func = lambda dominator_row, dominated_row: not any(
        dominator > dominated
        for dominator, dominated in zip(dominator_row, dominated_row))

    pareto_points = set()
    for candidate_row in points:
        candidate_stat = candidate_row[:-1] if ignore_last else candidate_row
        to_remove = set()
        for pareto_row in pareto_points:
            pareto_stat = pareto_row[:-1] if ignore_last else pareto_row
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


def sample_unique(points):
    random.seed(context.rand_seed)
    point_dict = collections.defaultdict(set)
    for *stats, expr in points:
        point_dict[tuple(stats)].add(expr)
    result_set = set()
    for stats, exprs in point_dict.items():
        expr = (exprs if len(exprs) == 1 else random.sample(exprs, 1)).pop()
        result_set.add(AnalysisResult(*(stats + (expr, ))))
    return result_set


def pareto_frontier(points, ignore_last=True):
    frontier = _pareto_frontier(points, ignore_last)[0]
    return frontier


def thick_frontier(points):
    frontier = []
    for _ in range(context.thickness + 1):
        optimal, points = _pareto_frontier(points)
        frontier += optimal
    return frontier


class Analysis(Flyweight):

    def __init__(self, expr_set, state, out_vars=None, size_limit=None):
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
        self.size_limit = size_limit or context.size_limit
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

        size = len(expr_set)
        limit = self.size_limit
        if limit >= 0 and size > limit:
            logger.debug(
                'Number of equivalent structures over limit {} > {}, '
                'reduces population size by sampling.'.format(size, limit))
            random.seed(context.rand_seed)
            expr_set = random.sample(expr_set, limit)

        results = set()
        step = 0
        total = len(expr_set)
        try:
            for expr in expr_set:
                step += 1
                logger.persistent(
                    'Analysing', '{}/{}'.format(step, total),
                    l=logger.levels.debug)
                result = self.analyze_expression(expr, state, out_vars)
                results.add(result)
        except KeyboardInterrupt:
            logger.warning(
                'Analysis interrupted, completed: {}.'.format(len(results)))
        logger.unpersistent('Analysing')

        self._results = results
        return results

    def analyze_expression(self, expr, state, out_vars):
        error = abs_error(expr, state)
        graph = schedule_graph(expr, out_vars)
        latency = graph.latency()
        resource = graph.resource_stats()
        return AnalysisResult(
            resource.lut, resource.dsp, error, latency, expr)

    def frontier(self):
        """Computes the Pareto frontier from analyzed results."""
        return sample_unique(pareto_frontier(self.analyze()))

    def thick_frontier(self):
        return thick_frontier(self.analyze())
