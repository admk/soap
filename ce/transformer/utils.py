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
    logger.debug('Expanding tree: %s' % str(tree))
    return transform(tree, [distribute_for_distributivity]).pop()


def parsings(tree):
    logger.debug('Generating parsings for tree: %s' % str(tree))
    return transform(tree, None, [associativity])


class MartelExpr(Expr):

    def traces(self, depth):
        def subtraces(a):
            try:
                return MartelExpr(a).traces(depth)
            except (ValueError, TypeError):
                return {a}
        stl = [subtraces(a) for a in self.args]
        sts = set(Expr(self.op, args) for args in itertools.product(*stl))
        logger.debug('Generating %s~=%d traces for tree: %s' %
                     ('*'.join([str(len(s)) for s in stl]),
                      len(sts), str(self)))
        cll = closure(sts, depth=depth)
        return cll

    def __repr__(self):
        return "MartelExpr(op='%s', a1=%s, a2=%s)" % \
            (self.op, repr(self.a1), repr(self.a2))


def martel(tree, depth=3):
    logger.debug('Generating martel for tree: %s' % str(tree))
    return MartelExpr(tree).traces(depth)


if __name__ == '__main__':
    import ce.logger as logger
    logger.set_context(level=logger.levels.debug)
    logger.info(expand('(a + 3) * (a + 3)'))
    logger.info(parsings('a + b + c'))
    logger.info(martel(expand('(a + 1) * (a + 1) * (a + 1)')))
