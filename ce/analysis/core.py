import gmpy2

import ce.logger as logger
from ce.common import DynamicMethods, Flyweight
from ce.expr import Expr
from ce.semantics import cast_error, mpfr


class Analysis(DynamicMethods, Flyweight):

    def __init__(self, expr_set):
        try:
            expr_set = {Expr(expr_set)}
        except TypeError:
            pass
        self.expr_set = expr_set
        super().__init__()

    def analyse(self):
        try:
            return self.result
        except AttributeError:
            pass
        analysis_names, analysis_methods, select_methods = self.methods()
        logger.debug('Analysing results.')
        result = []
        n = len(self.expr_set)
        for i, t in enumerate(self.expr_set):
            logger.persistent('Analysing', '%d/%d' % (i + 1, n),
                              l=logger.levels.debug)
            analysis_dict = {'expression': t}
            for name, func in zip(analysis_names, analysis_methods):
                analysis_dict[name] = func(t)
            result.append(analysis_dict)
        logger.unpersistent('Analysing')
        result = sorted(
            result, key=lambda k: tuple(k[n] for n in analysis_names))
        for analysis_dict in result:
            for n, f in zip(analysis_names, select_methods):
                analysis_dict[n] = f(analysis_dict[n])
        self.result = result
        return self.result

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

    def __init__(self, s, v):
        self.v = v
        super().__init__(s)

    def error_analysis(self, t):
        return t.error(self.v)

    def error_select(self, v):
        with gmpy2.local_context(round=gmpy2.RoundAwayZero):
            return float(mpfr(max(abs(v.e.min), abs(v.e.max))))


class AreaAnalysis(Analysis):

    def area_analysis(self, t):
        return t.area()

    def area_select(self, v):
        return v.area


def pareto_frontier_2d(s, keys=None):
    if keys:
        a = keys[1]
        sort_key = lambda e: tuple(e[k] for k in keys)
    else:
        a = 1
        sort_key = None
    s = sorted(s, key=sort_key)
    frontier = s[:1]
    for i, m in enumerate(s[1:]):
        if m[a] <= frontier[-1][a]:
            frontier.append(m)
    return frontier


class AreaErrorAnalysis(ErrorAnalysis, AreaAnalysis):
    """Collect area and error analysis."""

    def frontier(self):
        return pareto_frontier_2d(self.analyse(), keys=self.names())


if __name__ == '__main__':
    from ce.transformer import BiOpTreeTransformer
    logger.set_context(level=logger.levels.info)
    gmpy2.set_context(gmpy2.ieee(32))
    e = Expr('(a + b) * (a + b)')
    s = {
        'a': cast_error('5', '10'),
        'b': cast_error('0', '0.001')
    }
    a = AreaErrorAnalysis(BiOpTreeTransformer(e).closure(), s)
    a, f = a.analyse(), a.frontier()
    logger.info('Results', a)
    logger.info('Frontier', f)
