import gmpy2
import ce.logger as logger
from ce.common import timeit
from ce.expr import Expr
from ce.semantics import cast_error
from ce.analysis import analyse, Plot, expr_frontier
import ce.transformer.utils as utils


DEPTH = 2


@timeit
def closure(e, v):
    c = utils.closure(e)
    return c, set(expr_frontier(c, v))


@timeit
def depth(e, v):
    c = utils.closure(e, depth=DEPTH)
    return c, set(expr_frontier(c, v))


@timeit
def greedy(e, v):
    return None, utils.greedy_frontier_closure(e, depth=None, var_env=v)


@timeit
def frontier_trace(e, v):
    c = utils.frontier_trace(e, var_env=v, depth=DEPTH)
    return c, set(expr_frontier(c, v))


@timeit
def greedy_trace(e, v):
    c = utils.greedy_trace(e, v, depth=3)
    return c, set(expr_frontier(c, v))


gmpy2.set_context(gmpy2.ieee(32))
logger.set_context(level=logger.levels.debug)
Expr.__repr__ = Expr.__str__

e = '(a + a + b) * (a + b + b) * (b + b + c) * (c + c + a) * (c + a + a)'
v = {
    'a': cast_error('1', '2'),
    'b': cast_error('10', '20'),
    'c': cast_error('100', '200'),
}
p = Plot()
for f in [frontier_trace, greedy_trace]:
    derived, front = f(e, v)
    derived = derived or front
    logger.info(f.__name__, len(front), len(derived))
    p.add(analyse(derived, v), legend=f.__name__, annotate=False,
          alpha=0.7, linestyle='--', linewidth=2)
p.add(analyse(e, v), frontier=False, legend='original', marker='o')
p.save('a.pdf')
p.show()
