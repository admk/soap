import itertools

from ce.expr import Expr
from ce.transformer.core import TreeTransformer
from ce.transformer.biop import associativity, distribute_for_distributivity, \
    BiOpTreeTransformer
from ce.analysis import expr_frontier


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


def reduce(tree):
    try:
        tree = Expr(tree)
    except TypeError:
        return {reduce(t) for t in tree}
    s = set(transform(tree, BiOpTreeTransformer.reduction_methods))
    if len(s) > 1:
        s.remove(tree)
    if len(s) == 1:
        return s.pop()
    raise Exception


def parsings(tree):
    return transform(tree, None, [associativity])


def martel_closure(tree, depth=None):
    t = BiOpTreeTransformer(tree, depth=depth)
    t.transform_methods.remove(distribute_for_distributivity)
    return t.closure()


class MartelExpr(Expr):

    def traces(self, var_env=None, depth=None):
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
        cll = martel_closure(sts, depth=depth)
        if var_env:
            cll = expr_frontier(cll, var_env)
        return cll

    def __repr__(self):
        return "MartelExpr(op='%s', a1=%s, a2=%s)" % \
            (self.op, repr(self.a1), repr(self.a2))


def martel(tree, var_env=None, depth=2):
    return reduce(MartelExpr(expand(tree)).traces(var_env, depth))


if __name__ == '__main__':
    import ce.logger as logger
    from ce.common import timeit
    from ce.semantics import cast_error
    from ce.analysis import analyse, frontier, Plot
    logger.set_context(level=logger.levels.debug)
    Expr.__repr__ = Expr.__str__
    logger.info('Expand', expand('(a + 3) * (a + 3)'))
    logger.info('Parsings', parsings('a + b + c'))
    logger.info('Reduction', reduce('a + 2 * 3 * 4 + 6 * b + 3'))
    e = '(a + 2) * (b + 3) * c'
    v = {
        'a': cast_error('0.1', '0.2'),
        'b': cast_error('100', '200'),
        'c': cast_error('10000', '2000000'),
    }
    @timeit
    def closure_frontier(e, v):
        c = closure(e)
        return c, expr_frontier(c, v)
    complete, complete_front = closure_frontier(e, v)
    martel_front = timeit(martel)(e, v)
    logger.info('Closure', len(complete_front), complete_front)
    logger.info('Martel', len(martel_front), martel_front)
    p = Plot()
    p.add(analyse(complete, v), legend='Complete')
    p.add(analyse(martel_front, v), legend='Martel')
    p.show()
