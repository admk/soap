import gmpy2

import ce.logger as logger
from ce.common import DynamicMethods, Flyweight, cached
from ce.expr import Expr
from ce.semantics import cast_error, mpfr


class Analysis(DynamicMethods, Flyweight):

    def __init__(self, expr_set):
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
    from matplotlib import pyplot as plt
    from matplotlib.backends import backend_pdf
    from ce.transformer import BiOpTreeTransformer
    logger.set_context(level=logger.levels.info)
    gmpy2.set_context(gmpy2.ieee(32))
    e = Expr('((a + b) * (a + b))')
    s = {
        'a': cast_error('5', '10'),
        'b': cast_error('0', '0.001')
    }
    a = AreaErrorAnalysis(BiOpTreeTransformer(e).closure(), s)
    a, f = a.analyse(), a.frontier()
    ax = [v['area_analysis'] for v in a]
    ay = [float(v['error_analysis']) for v in a]
    fx = [v['area_analysis'] for v in f]
    fy = [float(v['error_analysis']) for v in f]
    for r in a:
        if r in f:
            logger.info('>', r['e'])
        else:
            logger.debug(' ', r['e'])
    fig = plt.figure()
    subplt = fig.add_subplot(111)
    subplt.set_ylim(0.8 * min(ay), 1.2 * max(ay))
    subplt.scatter(ax, ay)
    subplt.plot(fx, fy)
    plt.show()
    pp = backend_pdf.PdfPages('analysis.pdf')
    pp.savefig(fig)
    pp.close()
