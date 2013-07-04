import itertools

import ce.logger as logger
from ce.expr import Expr
from ce.transformer.core import TreeTransformer
from ce.transformer.biop import associativity, distribute_for_distributivity, \
    BiOpTreeTransformer
from ce.analysis import expr_frontier


def closure(tree, **kwargs):
    return BiOpTreeTransformer(tree, **kwargs).closure()


def greedy_frontier_closure(tree, depth=None, var_env=None):
    if var_env:
        func = lambda s: expr_frontier(s, var_env)
    else:
        func = None
    return BiOpTreeTransformer(
        tree, depth=depth, step_plugin=func).closure()


def transform(tree,
              reduction_methods=None, transform_methods=None,
              step_plugin=None, reduce_plugin=None, depth=None,
              multiprocessing=True):
    t = TreeTransformer(
        tree, step_plugin=step_plugin, reduce_plugin=reduce_plugin,
        depth=depth, multiprocessing=multiprocessing)
    t.reduction_methods = reduction_methods or []
    t.transform_methods = transform_methods or []
    return t.closure()


def expand(tree):
    def pop(s):
        if s:
            return [s.pop()]
        return s
    return transform(tree, reduction_methods=[distribute_for_distributivity],
                     reduce_plugin=pop, multiprocessing=False).pop()


def reduce(tree):
    try:
        tree = Expr(tree)
    except TypeError:
        with logger.local_context(level=logger.levels.info):
            return {reduce(t) for t in tree}
    t = transform(tree, BiOpTreeTransformer.reduction_methods,
                  multiprocessing=False)
    s = set(t)
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
