import itertools
import pickle
import shutil
import tempfile

from soap import logger
from soap.flopoco.common import cd, template_file, flopoco, xilinx


class _RTLGenerator(object):

    def __init__(self, expr, var_env, prec, file_name=None, dir=None):
        from soap.expression import Expr
        self.expr = Expr(expr)
        self.var_env = var_env
        self.wf = prec
        self.we = self.expr.exponent_width(var_env, prec)
        self.dir = dir or tempfile.mktemp(suffix='/')
        with cd(self.dir):
            self.f = file_name or tempfile.mktemp(suffix='.vhdl', dir=dir)

    def generate(self):
        from akpytemp import Template

        ops = set()
        in_ports = set()
        out_port, ls = self.expr.as_labels()
        wires = set()
        signals = set()

        def wire(op, in1, in2, out):
            def wire_name(i):
                if i in signals:
                    return i.signal_name()
                if i in in_ports:
                    return i.port_name()
                if i == out_port:
                    return 'p_out'
            for i in [in1, in2, out]:
                # a variable represented as a string is a port
                if isinstance(i.e, str):
                    in_ports.add(i)
                    continue
                # a number is a port
                try:
                    float(i.e)
                    in_ports.add(i)
                    continue
                except (TypeError, ValueError):
                    pass
                # a range is a port
                try:
                    a, b = i.e
                    float(a), float(b)
                    in_ports.add(i)
                    continue
                except (TypeError, ValueError):
                    pass
                # an expression, need a signal for its output
                try:
                    i.e.op
                    if i != out_port:
                        signals.add(i)
                except AttributeError:
                    pass
            wires.add((op, wire_name(in1), wire_name(in2), wire_name(out)))

        for out, e in ls.items():
            try:
                op, in1, in2 = e.op, e.a1, e.a2
                wire(op, in1, in2, out)
                ops.add(e.op)
            except AttributeError:
                pass
        in_ports = [i.port_name() for i in in_ports]
        out_port = 'p_out'
        signals = [i.signal_name() for i in signals]
        logger.debug(in_ports, signals, wires)
        Template(path=template_file).save(
            path=self.f, directory=self.dir, flopoco=flopoco,
            ops=ops, e=self.expr,
            we=self.we, wf=self.wf,
            in_ports=in_ports, out_port=out_port,
            signals=signals, wires=wires)
        return self.f


def actual_luts(expr, var_env, prec):
    import sh
    dir = tempfile.mktemp(suffix='/')
    f = _RTLGenerator(expr, var_env, prec, dir=dir).generate()
    logger.debug('Synthesising', str(expr), 'with precision', prec, 'in', f)
    try:
        return xilinx(f, dir=dir)
    except (sh.ErrorReturnCode, KeyboardInterrupt):
        raise
    finally:
        shutil.rmtree(dir)


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


_setup_rc_done = False


def _setup_rc():
    global _setup_rc_done
    if _setup_rc_done:
        return
    from matplotlib import rc
    rc('font', family='serif', size=24, serif='Times')
    rc('text', usetex=True)
    _setup_rc_done = True


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
        self.points = [p for p in self.points if p is not None]
        return self.points

    def _plot(self):
        try:
            return self.figure
        except AttributeError:
            pass
        from matplotlib import pyplot, pylab
        _setup_rc()
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
        from matplotlib import pyplot
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


def actual_vs_estimate():
    from soap.transformer.utils import greedy_trace
    from soap.flopoco.common import wf_range
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
