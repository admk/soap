from soap.analysis import Plot
from soap.transformer.utils import greedy_trace, frontier_trace, martel_trace
import soap.logger as logger

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
l = [
    (False, greedy_trace,   'x'),
    (False, frontier_trace, '+'),
    (True,  martel_trace,   'o'),
]
p = Plot(depth=3, var_env=v, legend_pos=(1.1, 0.5))
for s, f, m in l:
    if s:
        t = r'out of memory'
        fn = f.__name__
        f = lambda *args, **kwargs: []
        f.__name__ = fn
    else:
        t = True
    logger.info(f.__name__)
    p.add_analysis(e, func=f, marker=m,
                   legend=f.__name__, legend_time=t)
p.add_analysis(e, legend='original', marker='o', s=300)
p.save('motzkin.pdf')
p.show()
