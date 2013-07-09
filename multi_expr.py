import sys

from ce.analysis import Plot
from ce.transformer.utils import greedy_trace, frontier_trace
import ce.logger as logger

logger.set_context(level=logger.levels.debug)
vary_width = 'vary_width' in sys.argv
multi_expr = 'multi_expr' in sys.argv

e = """
    (a + a + b) * (a + b + b) * (b + b + c) *
    (b + c + c) * (c + c + a) * (c + a + a)
    """
if multi_expr:
    e += '| (1 + b + c) * (a + 1 + b) * (a + b + 1)'
v = {
    'a': ['1', '2'],
    'b': ['10', '20'],
    'c': ['100', '200'],
}
f = [frontier_trace, greedy_trace]
p = Plot(var_env=v, vary_width=vary_width)
p.add_analysis(e, func=frontier_trace, depth=2,
               marker='x', legend='frontier_trace')
p.add_analysis(e, func=greedy_trace, depth=3,
               marker='+', legend='greedy_trace')
p.add_analysis(e, legend='original', marker='o')
p.save('%s_expr_%s.pdf' %
       ('multi' if multi_expr else 'large',
        'vary_width' if vary_width else '32'))
p.show()
