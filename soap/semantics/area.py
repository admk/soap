"""
.. module:: soap.semantics.area
    :synopsis: The area semantics.
"""
import pickle
import itertools

from matplotlib import rc, pyplot, pylab

import soap.expr
import soap.logger as logger
from soap.common import Comparable
from soap.semantics import Lattice, flopoco


class AreaSemantics(Comparable, Lattice):
    """The semantics that captures the area of an expression."""
    def __init__(self, e, v, p):
        """Initialisation.

        :param e: The expression.
        :type e: class:`soap.expr.Expr`
        :param v: The ranges of input variables.
        :type v: dictionary containing mappings from variables to
            :class:`soap.semantics.error.Interval`
        :param p: Precision used to evaluate the expression, defaults to
            single precision.
        :type p: int

        Get the area estimation result with the property `area`.
        """
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
                if e.op == soap.expr.MULTIPLY_OP:
                    mult += 1
                if e.op == soap.expr.ADD_OP:
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


def _para_area(i_n_e_v_p):
    import sh
    i, n, e, v, p = i_n_e_v_p
    try:
        real_area, estimated_area = e.real_area(v, p), e.area(v, p).area
        logger.info(
            '%d/%d, Expr: %s, Prec: %d, Real Area: %d, Estimated Area: %d' %
            (i + 1, n, str(e), p, real_area, estimated_area))
        return real_area, estimated_area
    except sh.ErrorReturnCode:
        logger.error('Unable to synthesise', str(e), 'with precision', p)
    except Exception as exc:
        logger.error('Unknown failure', exc, 'when synthesising', str(e),
                     'with precision', p)


_pool = None


def pool():
    global _pool
    if _pool:
        return _pool
    from multiprocessing import Pool
    _pool = Pool()
    return _pool


class AreaEstimateValidator(object):
    """Validates our area model by comparing it against synthesis"""

    def __init__(self, expr_set=None, var_env=None, prec_list=None):
        self.e = expr_set
        self.v = var_env
        self.p = prec_list

    def scatter_points(self):
        try:
            return self.points
        except AttributeError:
            pass
        v = self.v
        n = len(self.e) * len(self.p)
        s = [(i, n, e, v, p)
             for i, (e, p) in enumerate(itertools.product(self.e, self.p))]
        self.points = pool().imap_unordered(_para_area, s)
        self.points = [p for p in self.points if not p is None]
        return self.points

    def _plot(self):
        try:
            return self.figure
        except AttributeError:
            pass
        self.figure = pyplot.figure()
        plot = self.figure.add_subplot(111)
        for ax in [plot.xaxis, plot.yaxis]:
            ax.get_major_formatter().set_scientific(True)
            ax.get_major_formatter().set_powerlimits((-2, 3))
        real_area, estimated_area = zip(*self.scatter_points())
        scatter_real_area = [v for i, v in enumerate(real_area) if i % 10 == 0]
        scatter_estimated_area = [v for i, v in enumerate(estimated_area)
                                  if i % 10 == 0]
        plot.scatter(scatter_real_area, scatter_estimated_area,
                     marker='.', s=0.5, linewidth=1, color='r')
        plot.grid(True, which='both', ls=':')
        plot.set_xlabel('Actual Area (Number of LUTs)')
        plot.set_ylabel('Estimated Area (Number of LUTs)')
        lim = max(plot.get_xlim())
        reg_fit = pylab.polyfit(real_area, estimated_area, 1)
        logger.info(reg_fit)
        reg_func = pylab.poly1d(reg_fit)
        plot.plot([0, lim], reg_func([0, lim]), color='k')
        plot.plot([0, lim], [0, lim], linestyle=':', color='k')
        plot.set_xlim(0, lim)
        plot.set_ylim(0, lim)
        return self.figure

    def show_plot(self):
        pyplot.show(self._plot())

    def save_plot(self, *args, **kwargs):
        self._plot().savefig(*args, bbox_inches='tight', **kwargs)

    @classmethod
    def load_points(cls, f):
        a = cls()
        with open(f, 'rb') as f:
            a.points = pickle.load(f)
        return a

    def save_points(self, f):
        p = self.scatter_points()
        with open(f, 'wb') as f:
            pickle.dump(p, f)


rc('font', family='serif', size=24, serif='Times')
rc('text', usetex=True)


if __name__ == '__main__':
    from soap.transformer.utils import greedy_trace
    from soap.semantics.flopoco import wf_range
    logger.set_context(level=logger.levels.info)
    try:
        a = AreaEstimateValidator.load_points('area.pkl')
    except FileNotFoundError:
        exprs = [
            """(a + a + b) * (a + b + b) * (b + b + c) *
               (b + c + c) * (c + c + a) * (c + a + a)""",
            '(1 + b + c) * (a + 1 + b) * (a + b + 1)',
            '(a + 1) * (b + 1) * (c + 1)',
            'a + b + c',
        ]
        v = {
            'a': ['1', '2'],
            'b': ['10', '20'],
            'c': ['100', '200'],
        }
        p = list(reversed(wf_range))
        s = []
        for e in exprs:
            s += greedy_trace(e, v, depth=3)
        a = AreaEstimateValidator(s, v, p)
        a.save_points('area.pkl')
    a.save_plot('area.pdf')
    a.show_plot()
