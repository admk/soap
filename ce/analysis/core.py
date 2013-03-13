#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


import itertools

from ..common import DynamicMethods
from ..expr import Expr, ExprTreeTransformer

from ..semantics import cast_error


class Analysis(DynamicMethods):

    def __init__(self, e, **kwargs):
        super(Analysis, self).__init__()
        self.e = e
        self.s = ExprTreeTransformer(Expr(e), **kwargs).closure()

    def analyse(self):
        a = sorted([self._analyse(t) for t in self.s],
                   key=lambda k: tuple(k[m.__name__] for m in self.methods()))
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
        super(ErrorAnalysis, self).__init__(e, **kwargs)
        self.v = v

    def error_analysis(self, t):
        return t.error(self.v)

    def error_select(self, d):
        m = self.error_analysis.__name__
        d[m] = float(max(abs(d[m].e.min), abs(d[m].e.max)))
        return d


if __name__ == '__main__':
    from pprint import pprint
    e = '((a + 0.25) + 0.75)'
    a = ErrorAnalysis(e, {'a': cast_error('0.01')}, print_progress=True)
    pprint(a.analyse())
