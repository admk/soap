from ce.analysis import Plot
from ce.transformer.utils import greedy_trace, frontier_trace, martel_trace
import ce.logger as logger

logger.set_context(level=logger.levels.debug)
e = '(a + b) * (a + b)'
v = {
    'a': ['5', '10'],
    'b': ['0', '0.001'],
}
d = 3
p = Plot(var_env=v, legend_pos=(1.1, 0.3))
p.add_analysis(e, func=martel_trace, depth=2, marker='.',
               legend='martel_trace', legend_time=True)
p.add_analysis(e, func=frontier_trace, depth=2, marker='x',
               legend='frontier_trace', legend_time=True)
p.add_analysis(e, func=greedy_trace, depth=3, marker='+',
               legend='greedy_trace', legend_time=True)
p.add_analysis(e, legend='original', marker='o')
p.save('martel.pdf')
p.show()
