import sys

from soap.analysis import Plot
from soap.transformer.utils import greedy_trace, frontier_trace, martel_trace
from soap.semantics.flopoco import wf_range
import soap.logger as logger

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
    (False, 2, frontier_trace, 'x', '-'),
    (False, 3, greedy_trace,   '.', '--'),
    (False, 2, greedy_trace,   '+', ':'),
    (True,  2, martel_trace,   'o',  ''),
]
if vary_width:
    t = [(False, 3, greedy_trace, '.', '-')]
    ss = 0.5
    w = 1.0
else:
    ss = 5
    w = 2.0
p = Plot(var_env=v, precs=(wf_range if vary_width else None))
for s, d, f, m, l in t:
    if vary_width:
        m = '.'
    logger.info('Processing', f.__name__)
    t = True
    if s:
        t = r'out of memory'
        fn = f.__name__
        f = lambda *args, **kwargs: []
        f.__name__ = fn
    p.add_analysis(e, func=f, depth=d,
                   marker=m, s=ss * 20, linestyle=l, linewidth=w,
                   legend=f.__name__, legend_time=t, legend_depth=True)
p.add_analysis(e, legend='original',
               marker='o', s=ss * 100, linewidth=w, facecolors='none')
p.save('multi_expr_%s.pdf' % ('vary_width' if vary_width else '32'))
p.show()
