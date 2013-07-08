from ce.analysis import Plot
from ce.transformer.utils import greedy_trace, frontier_trace
import ce.logger as logger

logger.set_context(level=logger.levels.debug)

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
f = [frontier_trace, greedy_trace]
p = Plot(var_env=v, vary_width=False)
p.add_analysis(e, func=frontier_trace, depth=2,
               marker='x', legend='frontier_trace, 2')
p.add_analysis(e, func=greedy_trace, depth=3,
               marker='+', legend='greedy_trace, 3')
p.add_analysis(e, legend='original', marker='o')
p.save('large_expr_32.pdf')
p.show()
