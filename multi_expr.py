import sys

from ce.analysis import Plot
from ce.transformer.utils import greedy_trace, frontier_trace
from ce.semantics.flopoco import wf_range
import ce.logger as logger

logger.set_context(level=logger.levels.info)
logger.set_context(pause_level=logger.levels.warning)
vary_width = 'vary_width' in sys.argv

e = """
    (a + a + b) * (a + b + b) * (b + b + c) *
    (b + c + c) * (c + c + a) * (c + a + a)
    """
e_y = '(1 + b + c) * (a + 1 + c) * (a + b + 1)'
e += ' | ' + e_y
v = {
    'a': ['1', '2'],
    'b': ['10', '20'],
    'c': ['100', '200'],
}
t = [
    (2, frontier_trace, 'x', '-'),
    (2, greedy_trace,   '+', '--'),
]
if vary_width:
    ss = 1
    w = 1.0
else:
    ss = 5
    w = 2.0
p = Plot(var_env=v, precs=(wf_range if vary_width else None))
for d, f, m, l in t:
    logger.info('Processing', f.__name__)
    p.add_analysis(e, func=f, depth=d,
                   marker=m, s=ss * 20, linestyle=l, linewidth=w,
                   legend=f.__name__, legend_time=True, legend_depth=True)
p.add_analysis(e, legend='original',
               marker='o', s=ss * 100, linewidth=w, facecolors='none')
p.save('multi_expr_%s.pdf' % ('vary_width' if vary_width else '32'))
p.show()
