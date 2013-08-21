import math

import soap.logger as logger
from soap.analysis import analyse_and_plot

logger.set_context(level=logger.levels.debug)

orders = list(range(2, 6))
s = []
for o in orders:
    e = ['1']
    for n in range(1, o):
        t = ' * '.join(['(x + y)'] * n)
        t = '(%d/%d) * %s' % ((-1) ** n, math.factorial(1 + 2 * n), t)
        e.append(t)
    e = ' + '.join(e)
    s.append(e)
s = [{'e': e, 'l': '$\mathrm{taylor}(\sin(x + y), %d)$' % o}
     for o, e in zip(orders, s)]
v = {
    'x': ['-0.1', '0.1'],
    'y': ['0', '1'],
}
d = 3
p = analyse_and_plot(s, v, d, o=True)
p.save('taylor_sin.pdf')
p.show()
