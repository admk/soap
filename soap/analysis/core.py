"""
.. module:: soap.analysis.core
    :synopsis: Analysis classes.
"""
import gmpy2

from soap import flopoco, logger
from soap.common import DynamicMethods, Flyweight
from soap.context import context
from soap.semantics import error_eval, ErrorSemantics, inf, luts


class Analysis(DynamicMethods, Flyweight):
    """A base class that analyses expressions for the quality metrics.

    This base class is not meant to be instantiated, but to be subclassed
    with methods to provide proper analysis.
    """

    def __init__(self, expr_set, var_env, out_vars=None, precs=None):
        """Analysis class initialisation.

        :param expr_set: A set of expressions or a single expression.
        :type expr_set: `set` or :class:`soap.expression.Expr`
        :param var_env: The ranges of input variables.
        :type var_env: dictionary containing mappings from variables to
            :class:`soap.semantics.error.Interval`
        :param precs: Precisions used to evaluate the expressions, defaults to
            the return value of :member:`precisions`.
        :type precs: list of integers
        """
        super().__init__()
        self.expr_set = expr_set
        self.var_env = var_env
        self.out_vars = out_vars
        self.precs = precs if precs else self.precisions()

    def precisions(self):
        """Returns the precisions being used.

        :returns: a list of integers indicating precisions.
        """
        return [context.precision]

    def analyse(self):
        """Analyses the set of expressions with input ranges and precisions
        provided in initialisation.

        :returns: a list of dictionaries each containing results and the
            expression.
        """
        try:
            return self.result
        except AttributeError:
            pass

        analysis_names, analysis_methods, select_methods = self.methods()

        logger.debug('Analysing results.')

        result = []
        i = 0
        total = len(self.expr_set) * len(self.precs)
        for prec in self.precs:
            for expr in self.expr_set:
                i += 1
                logger.persistent('Analysing', '%d/%d' % (i, total),
                                  l=logger.levels.debug)
                analysis_dict = {'expression': expr}
                for name, func in zip(analysis_names, analysis_methods):
                    analysis_dict[name] = func(expr, prec)
                result.append(analysis_dict)

        logger.unpersistent('Analysing')

        key_func = lambda k: tuple(k[name] for name in analysis_names)
        result = sorted(result, key=key_func)
        for analysis_dict in result:
            for name, func in zip(analysis_names, select_methods):
                analysis_dict[name] = func(analysis_dict[name])

        self.result = result
        return result

    @classmethod
    def names(cls):
        method_list = cls.list_method_names(lambda m: m.endswith('_analysis'))
        names = []
        for m in method_list:
            m = m.replace('_analysis', '')
            names.append(m)
        return names

    def methods(self):
        method_names = self.names()
        analysis_methods = []
        select_methods = []
        for m in method_names:
            analysis_methods.append(getattr(self, m + '_analysis'))
            select_methods.append(getattr(self, m + '_select'))
        return method_names, analysis_methods, select_methods


class ErrorAnalysis(Analysis):
    """This class provides the analysis of error bounds.

    It is a subclass of :class:`Analysis`.
    """
    def error_analysis(self, expr, prec):
        # FIXME precision
        return ErrorSemantics(error_eval(expr, self.var_env))

    def error_select(self, v):
        if v.is_bottom():
            logger.warning(
                'Cannot compute error for unreachable expression')
            return inf
        with gmpy2.local_context(gmpy2.ieee(64), round=gmpy2.RoundAwayZero):
            return float(max(abs(v.e.min), abs(v.e.max)))


class AreaAnalysis(Analysis):
    """This class provides the analysis of area estimation.

    It is a subclass of :class:`Analysis`.
    """
    def area_analysis(self, expr, prec):
        return luts(expr, self.var_env, self.out_vars, prec)

    def area_select(self, v):
        return v


def pareto_frontier_2d(s, keys=None):
    """Generates the 2D Pareto Frontier from a set of results.

    :param s: A set/list of comparable things.
    :type s: container
    :param keys: Keys used to compare items.
    :type keys: tuple or list
    """
    if keys:
        a = keys[1]
        sort_key = lambda e: tuple(e[k] for k in keys)
    else:
        a = 1
        sort_key = None
    s = sorted(s, key=sort_key)
    frontier = s[:1]
    for i, m in enumerate(s[1:]):
        if m[a] < frontier[-1][a]:
            frontier.append(m)
    return frontier


class AreaErrorAnalysis(ErrorAnalysis, AreaAnalysis):
    """Collect area and error analysis.

    It is a subclass of :class:`ErrorAnalysis` and :class:`AreaAnalysis`.
    """
    def frontier(self):
        """Computes the Pareto frontier from analysed results.
        """
        return pareto_frontier_2d(self.analyse(), keys=self.names())


class VaryWidthAnalysis(AreaErrorAnalysis):
    """Collect area and error analysis.

    It is a subclass of :class:`ErrorAnalysis` and :class:`AreaAnalysis`.
    """
    def precisions(self):
        """Allow precisions to vary in the range of `flopoco.wf_range`."""
        return flopoco.wf_range
