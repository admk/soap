import sys

from ce.common import invalidate_cache
from ce.analysis import Plot
from ce.transformer.utils import greedy_trace, frontier_trace
from ce.semantics.flopoco import wf_range
import ce.logger as logger

logger.set_context(level=logger.levels.debug)
logger.set_context(pause_level=logger.levels.warning)
vary_width = 'vary_width' in sys.argv
multi_expr = 'multi_expr' in sys.argv

e = """
    (a + a + b) * (a + b + b) * (b + b + c) *
    (b + c + c) * (c + c + a) * (c + a + a)
    """
if multi_expr:
    e += ' | (1 + b + c) * (a + 1 + c) * (a + b + 1)'
v = {
    'a': ['1', '2'],
    'b': ['10', '20'],
    'c': ['100', '200'],
}
p = Plot(var_env=v, precs=(wf_range if vary_width else None))
for d, f, m in [(2, frontier_trace, 'x'), (3, greedy_trace, '+')]:
    logger.info('Processing', f.__name__)
    p.add_analysis(e, func=f, depth=d, marker=m,
                   legend=f.__name__, legend_time=True)
p.add_analysis(e, legend='original', marker='o', facecolors='none')
p.save('%s_expr_%s.pdf' % ('multi' if multi_expr else 'large',
                           'vary_width' if vary_width else '32'))
p.show()
