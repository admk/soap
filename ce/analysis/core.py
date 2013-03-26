#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


import sys
import itertools

from ..common import DynamicMethods
from ..expr import Expr, ExprTreeTransformer

from ..semantics import cast_error


class Analysis(DynamicMethods):

    def __init__(self, e, print_progress=False, **kwargs):
        self.e = e
        self.s = ExprTreeTransformer(
            Expr(e), print_progress=print_progress, **kwargs).closure()
        self.p = print_progress
        super().__init__()

    def analyse(self):
        if self.p:
            print('Analysing results.')
        a = []
        n = len(self.s)
        for i, t in enumerate(self.s):
            if self.p:
                sys.stdout.write('\r%d/%d' % (i, n))
                sys.stdout.flush()
            a.append(self._analyse(t))
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
        d[m] = float(max(abs(d[m].e.min), abs(d[m].e.max)))
        return d


class AreaAnalysis(Analysis):

    def area_analysis(self, t):
        return t.area()

    def area_select(self, d):
        m = self.area_analysis.__name__
        d[m] = d[m].area
        return d


def pareto_frontier(s, keys=None):
    keys = keys or list(range(len(s[0])))
    s = sorted(s, key=lambda e: tuple(e[k] for k in keys))
    frontier = s[:]
    for m, n in itertools.product(s, s):
        if m == n:
            continue
        if not n in frontier:
            continue
        if all(m[k] <= n[k] for k in keys):
            if all(m[k] == n[k] for k in keys):
                continue
            frontier.remove(n)
    return frontier


class AreaErrorAnalysis(ErrorAnalysis, AreaAnalysis):
    """Collect area and error analysis."""

    def analyse(self):
        analysis = super().analyse()
        frontier = pareto_frontier(
            analysis, keys=(self.area_analysis.__name__,
                            self.error_analysis.__name__))
        return (analysis, frontier)


if __name__ == '__main__':
    from matplotlib import pyplot as plt
    e = '(((a + b) * (a + b)) * (a + b))'
    s = {
        'a': cast_error('0.01', '0.02'),
        'b': cast_error('0.02', '0.03')
    }
    a = AreaErrorAnalysis(e, s, print_progress=True)
    a, f = a.analyse()
    ax = [v['area_analysis'] for v in a]
    ay = [v['error_analysis'] for v in a]
    fx = [v['area_analysis'] for v in f]
    fy = [v['error_analysis'] for v in f]
    fig = plt.figure()
    subplt = fig.add_subplot(111)
    subplt.set_ylim(0.8 * min(ay), 1.2 * max(ay))
    subplt.scatter(ax, ay)
    subplt.plot(fx, fy)
    plt.show()
