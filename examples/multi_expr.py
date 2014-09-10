import sys

from soap import logger
from soap.analysis import Plot
from soap.context import context
from soap.parser import parse
from soap.semantics import BoxState, ErrorSemantics
from soap.transformer.discover import frontier, greedy, martel

logger.set_context(level=logger.levels.debug)
logger.set_context(pause_level=logger.levels.warning)
vary_width = 'vary_width' in sys.argv

e = parse("""
    (a + a + b) * (a + b + b) * (b + b + c) *
    (b + c + c) * (c + c + a) * (c + a + a)
    """)
# e_y = '(1 + b + c) * (a + 1 + c) * (a + b + 1)'
# e += ' | ' + e_y
v = BoxState({
    'a': ErrorSemantics(['1.0', '2.0'], [0, 0]),
    'b': ErrorSemantics(['10.0', '20.0'], [0, 0]),
    'c': ErrorSemantics(['100.0', '200.0'], [0, 0]),
})
t = [
    (False, 2, frontier, 'x', '-'),
    (False, 3, greedy,   '.', '--'),
    (False, 2, greedy,   '+', ':'),
    (True,  2, martel,   'o',  ''),
]
if vary_width:
    t = [(False, 3, greedy, '.', '-')]
    ss = 0.5
    w = 1.0
else:
    ss = 5
    w = 2.0
p = Plot(state=v, precs=[context.precision])
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
