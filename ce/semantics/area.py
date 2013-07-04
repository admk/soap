import sh
import itertools

from matplotlib import rc, pyplot

import ce.expr
import ce.logger as logger
from ce.common import Comparable
from ce.semantics import Lattice, flopoco


class AreaSemantics(Comparable, Lattice):

    def __init__(self, e, v, p):
        self.e = e
        self.v = v
        self.p = p
        self.l, self.s = e.as_labels()
        self.area = self._area()
        super().__init__()

    def join(self, other):
        pass

    def meet(self, other):
        pass

    def _op_counts(self):
        mult, add = 0, 0
        for _, e in self.s.items():
            try:
                if e.op == ce.expr.MULTIPLY_OP:
                    mult += 1
                if e.op == ce.expr.ADD_OP:
                    add += 1
            except AttributeError:
                pass
        return mult, add

    def _area(self):
        wf = self.p
        we = self.e.exponent_width(self.v, wf)
        mult, add = self._op_counts()
        return flopoco.adder(we, wf) * add + flopoco.multiplier(we, wf) * mult

    def __add__(self, other):
        return AreaSemantics(self.e + other.e, self.v)

    def __sub__(self, other):
        return AreaSemantics(self.e - other.e, self.v)

    def __mul__(self, other):
        return AreaSemantics(self.e * other.e, self.v)

    def __lt__(self, other):
        if not isinstance(other, AreaSemantics):
            return False
        return self.area < other.area

    def __eq__(self, other):
        if not isinstance(other, AreaSemantics):
            return False
        if self.area != other.area:
            return False
        return True

    def __str__(self):
        return str(self.area)

    def __repr__(self):
        return 'AreaSemantics(%s)' % repr(self.e)


class AreaEstimateValidator(object):

    def __init__(self, expr_set, var_env, prec_list):
        self.e = expr_set
        self.v = var_env
        self.p = prec_list

    def scatter_points(self):
        try:
            return self.points
        except AttributeError:
            pass
        points = []
        n = len(self.e) * len(self.p)
        try:
            for i, (e, p) in enumerate(itertools.product(self.e, self.p)):
                logger.persistent('Estimating', '%d/%d' % (i + 1, n))
                try:
                    points.append(
                        (e.real_area(self.v, p), e.area(self.v, p).area))
                except sh.ErrorReturnCode:
                    logger.error(
                        'Unable to synthesise', e, 'with precision', p)
        except KeyboardInterrupt:
            pass
        logger.unpersistent('Estimating')
        logger.info('Done estimation')
        self.points = points
        return points

    def _plot(self):
        self.figure = pyplot.figure()
        plot = self.figure.add_subplot(111)
        plot.scatter(*zip(*self.scatter_points()))
        plot.grid(True, which='both', ls=':')
        plot.set_xlabel('Actual Area (Number of LUTs)')
        plot.set_ylabel('Estimated Area (Number of LUTs)')
        return self.figure

    def show(self):
        self._plot()
        pyplot.show()

    def save(self, *args, **kwargs):
        self._plot().savefig(*args, **kwargs)


rc('font', family='serif', serif='Times')
rc('text', usetex=True)

if __name__ == '__main__':
    from ce.transformer.utils import closure
    from ce.semantics.flopoco import wf_range
    logger.set_context(level=logger.levels.info)
    e = ce.expr.Expr('(a + 1) * (b + 1)')
    v = {
        'a': ['0', '10'],
        'b': ['0', '1000'],
    }
    a = AreaEstimateValidator(closure(e, multiprocessing=False), v, wf_range)
    a.save('area.pdf')
