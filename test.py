import gmpy2
import ce.logger as logger
from ce.common import timeit
from ce.expr import Expr
from ce.analysis import analyse, Plot, expr_frontier
import ce.transformer.utils as utils


gmpy2.set_context(gmpy2.ieee(32))
logger.set_context(level=logger.levels.debug)
Expr.__repr__ = Expr.__str__


def analyse_and_plot(p, f, e, var_env=None, depth=None,
                     vary_width=False, legend=None):
    ts = time.time()
    derived = f(e, var_env=v, depth=depth)
    te = time.time()
    logger.info(f.__name__, len(derived))
    legend = legend or f.__name__ + ', depth=%d' % depth
    legend += ' (%f s)' % (te - ts)
    p.add(analyse(derived, v, vary_width=vary_width), legend=legend,
          alpha=0.7, linestyle='-', linewidth=1, marker='.')


e = """
    (a + a + b) * (a + b + b) * (b + b + c) *
    (b + c + c) * (c + c + a) * (c + a + a) |
    (1 + b + c) * (a + 1 + b) * (a + b + 1)
    """
v = {
    'a': ['1', '2'],
    'b': ['10', '20'],
    'c': ['100', '200'],
}
p = Plot()
for d in range(2, 8):
    analyse_and_plot(p, utils.greedy_trace, e, v, depth=d, legend=str(d))
p.add(analyse(e, v), frontier=False, legend='orig', marker='.')
p.save('a.pdf')
p.show()
