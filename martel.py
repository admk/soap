from ce.analysis import Plot
from ce.transformer.utils import greedy_trace, frontier_trace, martel_trace
from ce.semantics import ErrorSemantics
import ce.logger as logger

logger.set_context(level=logger.levels.info)
e = '(a + b) * (a + b)'
v = {
    'a': ErrorSemantics(['5', '10'], ['0', '0']),
    'b': ['0', '0.001'],
}
t = [
    (None, greedy_trace,   'x', '-'),
    (None, frontier_trace, '+', '-'),
    (None, martel_trace,   '.', '-'),
]
d = 3
s = 100
p = Plot(var_env=v, depth=d, legend_pos=(0.55, 0.35))
p.add_analysis(e, legend='original', marker='o', s=200, facecolors='none')
for d, f, m, l in t:
    logger.info('Processing', f.__name__)
    p.add_analysis(e, func=f, depth=d, marker=m, s=s, linestyle=l,
                   legend=f.__name__, legend_time=True, legend_depth=True)
p.save('martel.pdf')
p.show()
