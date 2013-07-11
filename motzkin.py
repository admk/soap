from ce.analysis import Plot
from ce.transformer.utils import greedy_trace, frontier_trace
import ce.logger as logger

logger.set_context(level=logger.levels.debug)


mul = lambda *args: ' * '.join(args)
add = lambda *args: ' + '.join(args)
pow = lambda v, o: mul(*([v] * o))

# $z^3 + x^4 y^2 + x^2 y^4 - 3 x^2 y^2 z^2$
e = [pow('z', 3), mul(pow('x', 4), pow('y', 2)), mul(pow('x', 2), pow('y', 4)),
     mul('-3', pow('x', 2), pow('y', 2), pow('z', 2))]
e = add(*e)
v = {
    'x': ['0.99', '1'],
    'y': ['1', '1.01'],
    'z': ['-0.01', '0.01'],
}
d = 3
p = Plot(var_env=v, legend_pos=(1.1, 0.3))
p.add_analysis(e, func=frontier_trace, depth=2, marker='x',
               legend='frontier_trace', legend_time=True)
p.add_analysis(e, func=greedy_trace, depth=3, marker='+',
               legend='greedy_trace', legend_time=True)
p.add_analysis(e, legend='original', marker='o')
p.save('motzkin.pdf')
p.show()
