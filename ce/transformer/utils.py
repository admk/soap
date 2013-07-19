import itertools

import ce.logger as logger
from ce.expr import Expr
from ce.transformer.core import TreeTransformer
from ce.transformer.biop import associativity, distribute_for_distributivity, \
    BiOpTreeTransformer
from ce.analysis import expr_frontier


def closure(tree, **kwargs):
    return BiOpTreeTransformer(tree, **kwargs).closure()


def greedy_frontier_closure(tree, var_env=None, prec=None, **kwargs):
    if var_env:
        func = lambda s: expr_frontier(s, var_env, prec)
    else:
        func = None
    closure = BiOpTreeTransformer(tree, step_plugin=func, **kwargs).closure()
    return expr_frontier(closure, var_env, prec)


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

    def traces(self, var_env=None, depth=None, prec=None, **kwargs):
        _, discovered = self._traces(var_env, depth, prec, **kwargs)
        return discovered

    def _traces(self, var_env=None, depth=None, prec=None, **kwargs):
        subtraces = []
        discovered = []
        for a in self.args:
            try:
                arg_subtraces, arg_discovered = \
                    self.__class__(a)._traces(var_env, depth, prec, **kwargs)
            except (ValueError, TypeError):
                arg_subtraces = arg_discovered = {a}
            subtraces.append(arg_subtraces)
            discovered.append(arg_discovered)
        list_to_expr_set = lambda st: \
            set(Expr(self.op, args) for args in itertools.product(*st))
        subtraces = list_to_expr_set(subtraces)
        logger.debug('Generating %d traces for tree: %s' %
                     (len(subtraces), str(self)))
        closure = set(self.closure(
            subtraces, depth=depth, var_env=var_env, prec=prec, **kwargs))
        return closure, closure | subtraces | list_to_expr_set(discovered)

    def clousure(self, trees, **kwargs):
        raise NotImplementedError

    def __repr__(self):
        return "TraceExpr(op='%s', a1=%s, a2=%s)" % \
            (self.op, repr(self.a1), repr(self.a2))


class MartelTraceExpr(TraceExpr):
    def closure(self, trees, **kwargs):
        return closure(trees, depth=kwargs['depth'])


class GreedyTraceExpr(TraceExpr):
    def closure(self, trees, **kwargs):
        return greedy_frontier_closure(trees, **kwargs)


class FrontierTraceExpr(TraceExpr):
    def closure(self, trees, **kwargs):
        return expr_frontier(closure(trees, depth=kwargs['depth']),
                             kwargs['var_env'], prec=kwargs['prec'])


def martel_trace(tree, var_env=None, depth=2, prec=None, **kwargs):
    return reduce(MartelTraceExpr(tree).traces(var_env, depth, prec, **kwargs))


def greedy_trace(tree, var_env=None, depth=2, prec=None, **kwargs):
    return reduce(GreedyTraceExpr(tree).traces(var_env, depth, prec, **kwargs))


def frontier_trace(tree, var_env=None, depth=2, prec=None, **kwargs):
    return reduce(FrontierTraceExpr(tree).traces(
                  var_env, depth, prec, **kwargs))
