from soap.analysis import Plot
from soap.transformer.utils import greedy_trace, frontier_trace, martel_trace
from soap.semantics import ErrorSemantics
import soap.logger as logger

logger.set_context(level=logger.levels.info)
e = '(a + b) * (a + b)'
v = {
    'a': ErrorSemantics(['5', '10'], ['0', '0']),
    'b': ['0', '0.001'],
}
t = [
    (None, greedy_trace,   'x', '-', 'r'),
    (None, frontier_trace, '+', '-', 'g'),
    (None, martel_trace,   '.', '-', 'b'),
]
d = 3
s = 200
p = Plot(var_env=v, depth=d, legend_pos=(0.55, 0.35))
p.add_analysis(e, legend='original', marker='o', s=400, color='k')
for d, f, m, l, c in t:
    logger.info('Processing', f.__name__)
    p.add_analysis(e, func=f, depth=d, marker=m, s=s, linestyle=l, color=c,
                   legend=f.__name__, legend_time=True, legend_depth=True)
p.save('martel.pdf')
p.show()
