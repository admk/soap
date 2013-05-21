import itertools

import ce.logger as logger
from ce.expr import Expr
from ce.transformer.core import TreeTransformer
from ce.transformer.biop import associativity, distribute_for_distributivity, \
    BiOpTreeTransformer
from ce.analysis import expr_frontier


def closure(tree, depth=None):
    return BiOpTreeTransformer(tree, depth=depth).closure()


def greedy_frontier_closure(tree, depth=None, var_env=None):
    if var_env:
        func = lambda s: expr_frontier(s, var_env)
    else:
        func = None
    return BiOpTreeTransformer(
        tree, depth=depth, plugin_function=func).closure()


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


def collecting_closure(tree, depth=None):
    t = BiOpTreeTransformer(tree, depth=depth)
    t.transform_methods.remove(distribute_for_distributivity)
    return t.closure()


class TraceExpr(Expr):

    def traces(self, var_env=None, depth=None):
        def subtraces(a):
            try:
                return self.__class__(a).traces(var_env, depth)
            except (ValueError, TypeError):
                return {a}
        stl = [subtraces(a) for a in self.args]
        sts = set(Expr(self.op, args) for args in itertools.product(*stl))
        logger.debug('Generating %s~=%d traces for tree: %s' %
                     ('*'.join([str(len(s)) for s in stl]),
                      len(sts), str(self)))
        cls = set(self.closure(sts, depth=depth, var_env=var_env))
        return cls | sts

    def clousure(self, trees, **kwargs):
        raise NotImplementedError

    def __repr__(self):
        return "TraceExpr(op='%s', a1=%s, a2=%s)" % \
            (self.op, repr(self.a1), repr(self.a2))


class GreedyTraceExpr(TraceExpr):
    def closure(self, trees, **kwargs):
        return greedy_frontier_closure(trees, **kwargs)


class FrontierTraceExpr(TraceExpr):
    def closure(self, trees, **kwargs):
        return expr_frontier(
            closure(trees, depth=kwargs['depth']), kwargs['var_env'])


def greedy_trace(tree, var_env=None, depth=2):
    return reduce(GreedyTraceExpr(tree).traces(var_env, depth))


def frontier_trace(tree, var_env=None, depth=2):
    return reduce(FrontierTraceExpr(tree).traces(var_env, depth))


if __name__ == '__main__':
    import ce.logger as logger
    from ce.common import timeit
    from ce.semantics import cast_error
    from ce.analysis import analyse, Plot
    logger.set_context(level=logger.levels.debug)
    Expr.__repr__ = Expr.__str__

    depth = 2

    @timeit
    def closure_frontier(e, v):
        c = closure(e)
        return c, set(expr_frontier(c, v))

    @timeit
    def depth_frontier(e, v):
        c = collecting_closure(expand(e), depth=depth)
        return c, set(expr_frontier(c, v))

    @timeit
    def martel_frontier(e, v):
        return None, martel(e, v, depth=depth)

    logger.info('Expand', expand('(a + 3) * (a + 3)'))
    logger.info('Parsings', parsings('a + b + c'))
    logger.info('Reduction', reduce('a + 2 * 3 * 4 + 6 * b + 3'))

    e = '(a + 2) * (b + 3) * (c + 4)'
    v = {
        'a': cast_error('0.1', '0.2'),
        'b': cast_error('100', '200'),
        'c': cast_error('10000', '2000000'),
        'd': cast_error('0.1', '0.2'),
    }
    p = Plot()
    for f in [depth_frontier, martel_frontier]:
        derived, front = f(e, v)
        logger.info(f.__name__, len(front), front)
        derived = derived or front
        p.add(analyse(derived, v),
              legend=f.__name__, alpha=0.7, linestyle='--')
    p.add(analyse(e, v), frontier=False, legend='Original')
    p.show()
