import itertools

from ce.expr import Expr
from ce.transformer.core import TreeTransformer
from ce.transformer.biop import associativity, distribute_for_distributivity, \
    BiOpTreeTransformer


def closure(tree, depth=None):
    return BiOpTreeTransformer(tree, depth=depth).closure()


def transform(tree,
              reduction_methods=None, transform_methods=None, depth=None):
    t = TreeTransformer(tree)
    t.reduction_methods = reduction_methods or []
    t.transform_methods = transform_methods or []
    return t.closure()


def expand(tree):
    return transform(tree, [distribute_for_distributivity]).pop()


def parsings(tree):
    return transform(tree, None, [associativity])


class MartelExpr(Expr):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def traces(self, depth):
        def subtraces(a):
            try:
                return a.traces(depth)
            except AttributeError:
                return {a}
        stl = [subtraces(a) for a in self.args]
        cll = [closure(Expr(self.op, args), depth=depth)
               for args in itertools.product(*stl)]
        return set.intersection(*cll)


def martel(tree, depth=3):
    return MartelExpr(tree).traces(depth)


if __name__ == '__main__':
    import ce.logger as logger
    logger.set_context(level=logger.levels.debug)
    logger.info(expand('(a + 3) * (a + 3)'))
    logger.info(parsings('a + b + c'))
    logger.info(martel(expand('(a + 1) * (a + 1) * (a + 1)')))
