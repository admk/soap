"""
.. module:: soap.transformer.martel
    :synopsis: Some compatibility hacks to support martel's equivalence
        finding, so we can compare.
"""
from soap.transformer.arithmetic import ArithTreeTransformer


class MartelTreeTransformer(ArithTreeTransformer):

    reduction_methods = []

    def _harvest(self, trees):
        return trees

    def _seed(self, trees):
        return trees

    def _step(self, expressions, closure=False, depth=None):
        return super()._step(expressions, closure, self.depth)
