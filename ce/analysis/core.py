#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :

from .. import DynamicMethods
from ..expr import Expr, ExprTreeTransformer
from ..semantics import ErrorSemantics, cast


class Analysis(DynamicMethods):

    def __init__(self, e, **kwargs):
        super(Analysis, self).__init__()
        self.e = e
        self.s = ExprTreeTransformer(Expr(e), **kwargs).closure()

    def analyse(self):
        return [(self._analyse(t), t) for t in self.s]

    def _analyse(self, t):
        l = self.list_methods(lambda m: m.endswith('analysis'))
        return (f(r) for f in l)


class ErrorAnalysis(Analysis):

    def __init__(self, e, v, **kwargs):
        super(ErrorAnalysis, self).__init__(e, **kwargs)
        self.v = v

    def error_analysis(self, t):
        return t.error(self.v)
