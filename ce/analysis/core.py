import gmpy2

import ce.logger as logger
from ..common import DynamicMethods
from ..expr import Expr, BiOpTreeTransformer
from ..semantics import cast_error, mpfr


class Analysis(DynamicMethods):

    def __init__(self, e, **kwargs):
        self.e = e
        self.s = BiOpTreeTransformer(Expr(e), **kwargs).closure()
        super().__init__()

    def analyse(self):
        logger.info('Analysing results.')
        a = []
        n = len(self.s)
        for i, t in enumerate(self.s):
            logger.persistent('Analysing', '%d/%d' % (i + 1, n))
            a.append(self._analyse(t))
        logger.unpersistent('Analysing')
        a = sorted(
            a, key=lambda k: tuple(k[m.__name__] for m in self.methods()))
        return [self._select(d) for d in a]

    def _analyse(self, t):
        d = {'e': t}
        d.update({m.__name__: m(t) for m in self.methods()})
        return d

    def _select(self, d):
        d['e'] = str(d['e'])
        for f in self.list_methods(lambda m: m.endswith('select')):
            d = f(d)
        return d

    def methods(self):
        return self.list_methods(lambda m: m.endswith('analysis'))


class ErrorAnalysis(Analysis):

    def __init__(self, e, v, **kwargs):
        self.v = v
        super().__init__(e, **kwargs)

    def error_analysis(self, t):
        return t.error(self.v)

    def error_select(self, d):
        m = self.error_analysis.__name__
        with gmpy2.local_context(round=gmpy2.RoundAwayZero):
            d[m] = mpfr(max(abs(d[m].e.min), abs(d[m].e.max)))
        return d


class AreaAnalysis(Analysis):

    def area_analysis(self, t):
        return t.area()

    def area_select(self, d):
        m = self.area_analysis.__name__
        d[m] = d[m].area
        return d


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

    def analyse(self):
        analysis = super().analyse()
        frontier = pareto_frontier_2d(
            analysis, keys=(self.area_analysis.__name__,
                            self.error_analysis.__name__))
        return (analysis, frontier)


if __name__ == '__main__':
    from matplotlib import pyplot as plt
    from matplotlib.backends import backend_pdf
    logger.set_context(level=logger.levels.info)
    gmpy2.set_context(gmpy2.ieee(32))
    e = Expr('((a + b) * (a + b))')
    s = {
        'a': cast_error('5', '10'),
        'b': cast_error('0', '0.001')
    }
    a = AreaErrorAnalysis(e, s)
    a, f = a.analyse()
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
