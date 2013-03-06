#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


from ..common import DynamicMethods
from ..expr import Expr, ExprTreeTransformer

from ..semantics import cast_error


class Analysis(DynamicMethods):

    def __init__(self, e, **kwargs):
        super(Analysis, self).__init__()
        self.e = e
        self.s = ExprTreeTransformer(Expr(e), **kwargs).closure()

    def analyse(self):
        return sorted([self.select(self._analyse(t), t) for t in self.s])

    def _analyse(self, t):
        l = self.list_methods(lambda m: m.endswith('analysis'))
        return tuple(f(t) for f in l)

    def select(self, r, e):
        return (r, e)


class ErrorAnalysis(Analysis):

    def __init__(self, e, v, **kwargs):
        super(ErrorAnalysis, self).__init__(e, **kwargs)
        self.v = v

    def error_analysis(self, t):
        return t.error(self.v)

    def select(self, r, e):
        r = float(max(abs(r[0].e.min), abs(r[0].e.max)))
        return (r, str(e))

if __name__ == '__main__':
    from pprint import pprint
    e = '((a + 0.1) + 0.4)'
    a = ErrorAnalysis(e, {'a': cast_error('0.1', '0.2')}, print_progress=True)
    pprint(a.analyse())
