import time
import gmpy2

import ce.logger as logger
from ce.expr import Expr
from ce.analysis import analyse, Plot
import ce.transformer.utils as utils


gmpy2.set_context(gmpy2.ieee(32))
logger.set_context(level=logger.levels.debug)
Expr.__repr__ = Expr.__str__


def analyse_and_plot(p, f, e, var_env=None, depth=None,
                     vary_width=False, legend=None):
    ts = time.time()
    derived = f(e, var_env=v, depth=depth)
    te = time.time()
    td = ' (%f s)' % (te - ts)
    logger.info(f.__name__, len(derived), td)
    legend = legend or f.__name__ + ', depth=%d' % depth
    legend += td
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
try:
    for d in range(2, 8):
        logger.info('Depth:', d)
        analyse_and_plot(p, utils.greedy_trace, e, v, depth=d, legend=str(d))
except KeyboardInterrupt:
    pass
p.add(analyse(e, v), frontier=False, legend='orig', marker='.')
p.save('analysis.pdf')
p.show()
