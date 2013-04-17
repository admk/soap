import gmpy2

import ce.logger as logger
from ce.common import DynamicMethods, Flyweight, cached
from ce.expr import Expr
from ce.semantics import cast_error, mpfr


class Analysis(DynamicMethods, Flyweight):

    def __init__(self, s):
        self.s = s
        super().__init__()

    def analyse(self):
        try:
            return self.result
        except AttributeError:
            pass
        logger.debug('Analysing results.')
        a = []
        n = len(self.s)
        for i, t in enumerate(self.s):
            logger.persistent('Analysing', '%d/%d' % (i + 1, n),
                              l=logger.levels.debug)
            a.append(self._analyse(t))
        logger.unpersistent('Analysing')
        a = sorted(
            a, key=lambda k: tuple(k[m.__name__] for m in self.methods()))
        self.result = [self._select(d) for d in a]
        return self.result

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

    def __init__(self, s, v):
        self.v = v
        super().__init__(s)

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

    def frontier(self):
        return pareto_frontier_2d(
            self.analyse(), keys=(self.area_analysis.__name__,
                                  self.error_analysis.__name__))


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
