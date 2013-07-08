import math
from ce.analysis import analyse_and_plot

s = ['1 + ' + ' + '.join(
     '(%d/%d) * %s' %
     ((-1) ** n, math.factorial(1 + 2 * n),
      ' * '.join(['(a + b)'] * n)) for n in range(1, o))
     for o in range(2, 6)]
s = [(e, '$\mathrm{taylor}(\sin(a + b), %d)$' % o) for o, e in enumerate(s)]
v = {
    'a': [-0.1, 0.1],
    'b': [0, 1],
}
d = 3
p = analyse_and_plot(s, v, d)
p.save('taylor(sin(a + b)).pdf')
p.show()
