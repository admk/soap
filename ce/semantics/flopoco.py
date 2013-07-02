import os
import sh
from contextlib import contextmanager

from ce.common import cached, timeit
from ce.semantics import Label
from ce.expr import Expr, ADD_OP, MULTIPLY_OP


class FlopocoMissingImplementationError(Exception):
    """Unsynthesizable operator"""


we_min, we_max = 5, 16
wf_min, wf_max = 10, 113
we_range = list(range(we_min, we_max))
wf_range = list(range(wf_min, wf_max))
default_file = 'ce/semantics/area.pkl'
device = 'xc6vlx760'


@contextmanager
def cd(d):
    p = os.path.abspath(os.curdir)
    if d:
        sh.mkdir('-p', d)
        sh.cd(d)
    yield
    sh.cd(p)


def get_luts(file_name):
    from bs4 import BeautifulSoup
    with open(file_name, 'r') as f:
        f = BeautifulSoup(f.read())
        app = f.document.application
        util = app.find('section', stringid='XST_DEVICE_UTILIZATION_SUMMARY')
        luts = util.find('item', stringid='XST_NUMBER_OF_SLICE_LUTS')
        return luts.get('value')


def flopoco(op, we, wf, f):
    flo_fn = 'flopoco.vhdl'
    flo_cmd = []
    if op == 'add':
        flo_cmd += ['FPAdder', we, wf]
    elif op == 'mul':
        flo_cmd += ['FPMultiplier', we, wf, wf]
    wd, fn = os.path.split(f)
    with cd(wd):
        try:
            sh.flopoco(*flo_cmd)
            if fn != flo_fn:
                sh.mv(flo_fn, fn)
        except sh.ErrorReturnCode as e:
            print('Flopoco failed', op, we, wf)
    return op, we, wf, f


def xilinx(op, we, wf, f):
    wd, fn = os.path.split(f)
    g = os.path.splitext(fn)[0] + '.ngc'
    with cd(wd):
        try:
            sh.xst(sh.echo('run', '-p', device,
                           '-ifn', fn, '-ifmt', 'VHDL',
                           '-ofn', g, '-ofmt', 'NGC'))
            item = dict(op=op, we=we, wf=wf, value=get_luts(g + '_xst.xrpt'))
        except sh.ErrorReturnCode as e:
            print('Xilinx failed', op, we, wf)
            item = dict(op=op, we=we, wf=wf, value=-1)
    if wd:
        sh.rm('-rf', wd)
    return item


def synth_eval(op, we, wf):
    work_dir = 'syn_%d' % os.getpid()
    f = os.path.join(work_dir, '%s_%d_%d.vhdl' % (op, we, wf))
    print('Processing', op, we, wf)
    item = xilinx(*flopoco(op, we, wf, f=f))
    print(item)
    return item


@timeit
def _para_synth(op_we_wf):
    return synth_eval(*op_we_wf)


pool = None


@timeit
def batch_synth(we_range, wf_range):
    import itertools
    from multiprocessing import Pool
    global pool
    if not pool:
        pool = Pool(8)
    args = itertools.product(['add', 'mul'], we_range, wf_range)
    return list(pool.imap_unordered(_para_synth, args))


def load(file_name):
    import pickle
    with open(file_name, 'rb') as f:
        return pickle.loads(f.read())


def save(file_name, results):
    import pickle
    with open(file_name + '.pkl', 'wb') as f:
        pickle.dump(results, f)


def plot(results):
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    fig = plt.figure()
    ax = Axes3D(fig)
    vl = []
    for i in results:
        xv, yv, zv = int(i['we']), int(i['wf']), int(i['value'])
        if zv < 0:
            continue
        vl.append((xv, yv, zv))
    ax.scatter(*zip(*vl))
    plt.show()


if not os.path.isfile(default_file):
    print('area statistics file does not exist, synthesizing...')
    save(default_file, batch_synth(we_range, wf_range))

_add = {}
_mul = {}
for i in load(default_file):
    xv, yv, zv = int(i['we']), int(i['wf']), int(i['value'])
    if zv <= 0:
        continue
    if i['op'] == 'add':
        _add[xv, yv] = zv
    elif i['op'] == 'mul':
        _mul[xv, yv] = zv


def _impl(_dict, we, wf):
    try:
        return _dict[we, wf]
    except KeyError:
        if not wf in wf_range:
            raise FlopocoMissingImplementationError(
                'Precision %d out of range' % wf)
        elif not we in we_range:
            raise FlopocoMissingImplementationError(
                'Exponent width %d out of range' % we)
        return _impl(_dict, we + 1, wf)


def adder(we, wf):
    return _impl(_add, we, wf)


def multiplier(we, wf):
    return _impl(_mul, we, wf)


@cached
def keys():
    return sorted(list(set(_add.keys()) & set(_mul.keys())))


class CodeGenerator(object):

    def __init__(self, expr, var_env, prec):
        self.expr = Expr(expr)
        self.var_env = var_env
        self.wf = prec
        self.we = self.expr.exponent_width(var_env, prec)

    def generate_op(op):
        from ce.semantics.flopoco import flopoco
        if op == ADD_OP:
            op = 'add'
        elif op == MULTIPLY_OP:
            op = 'mul'
        f = '%s_%d_%d.vhdl' % (op, self.we, self.wf)
        flopoco(op, self.we, self.wf, f)

    def generate(self):
        l, ls = self.expr.as_labels()
        ops = []
        in_ports = []
        out_port = l
        wires = []
        signals = []
        def wire_name(i):
            if i in in_ports or i == out_port:
                return i.port_name()
            elif i in signals:
                return i.signal_name()
        def wire(op, in1, in2, out):
            for i in [in1, in2, out]:
                # a variable represented as a string is a port
                if isinstance(i.e, str):
                    in_ports.append(i)
                # a number is a port
                try:
                    float(i.e)
                    in_ports.append(i)
                except (TypeError, ValueError):
                    pass
                # an expression, need a signal for its output
                try:
                    i.e.op
                    if not i in signals and i != l:
                        signals.append(i)
                    continue
                except AttributeError:
                    pass
            wires.append((op, wire_name(in1), wire_name(in2), wire_name(out)))
        for out, e in ls.items():
            try:
                op, in1, in2 = e.op, e.a1, e.a2
                wire(op, in1, in2, out)
                if not op in ops:
                    ops.append(e.op)
            except AttributeError:
                pass
        in_ports = [i.port_name() for i in in_ports]
        out_port = out_port.port_name()
        signals = [i.signal_name() for i in signals]


if __name__ == '__main__':
    plot(load(default_file))
    CodeGenerator('a + b + 1', {'a': ['0', '1'], 'b': ['0', '100']}, 23).generate()
