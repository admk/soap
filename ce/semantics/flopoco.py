import os
import sh
import tempfile
from contextlib import contextmanager

from ce.common import cached, timeit
import ce.logger as logger


class FlopocoMissingImplementationError(Exception):
    """Unsynthesizable operator"""


we_min, we_max = 5, 15
wf_min, wf_max = 10, 112
we_range = list(range(we_min, we_max + 1))
wf_range = list(range(wf_min, wf_max + 1))

directory = 'ce/semantics/'
default_file = directory + 'area.pkl'
template_file = directory + 'template.vhdl'

device_name = 'Virtex6'
device_model = 'xc6vlx760'


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


def flopoco(op, we, wf, f=None, dir=None):
    from ce.expr import ADD_OP, MULTIPLY_OP
    flopoco_cmd = []
    flopoco_cmd += ['-target=' + device_name]
    dir = dir or tempfile.mktemp(suffix='/')
    with cd(dir):
        if f is None:
            f = tempfile.mktemp(suffix='.vhdl', dir=dir)
        flopoco_cmd += ['-outputfile=%s' % f]
        if op == 'add' or op == ADD_OP:
            flopoco_cmd += ['FPAdder', we, wf]
        elif op == 'mul' or op == MULTIPLY_OP:
            flopoco_cmd += ['FPMultiplier', we, wf, wf]
        else:
            raise ValueError('Unrecognised operator %s' % str(op))
        sh.flopoco(*flopoco_cmd)
    return dir, f


def xilinx(f, dir=None):
    file_base = os.path.split(f)[1]
    file_base = os.path.splitext(file_base)[0]
    g = file_base + '.ngc'
    cmd = ['run', '-p', device_model]
    cmd += ['-ifn', f, '-ifmt', 'VHDL']
    cmd += ['-ofn', g, '-ofmt', 'NGC']
    dir = dir or tempfile.mktemp(suffix='/')
    with cd(dir):
        sh.xst(sh.echo(*cmd), _out='out.log', _err='err.log')
        return get_luts(file_base + '.ngc_xst.xrpt')


def eval_operator(op, we, wf, f=None, dir=None):
    dir, f = flopoco(op, we, wf, f, dir)
    return dict(op=op, we=we, wf=wf, value=xilinx(f, dir))


@timeit
def _para_synth(op_we_wf):
    op, we, wf = op_we_wf
    logger.info('Processing', op, we, wf)
    work_dir = 'syn_%d' % os.getpid()
    with cd(work_dir):
        try:
            item = eval_operator(op, we, wf, f=None, dir=work_dir)
            logger.info(item)
            return item
        except sh.ErrorReturnCode as e:
            logger.error('Command failed:')
            logger.error(e.full_cmd, e.args)
            logger.error('Standard Output:')
            logger.error(str(e.stdout).replace('\\n', '\n'))
            logger.error('Standard Error Output:')
            logger.error(str(e.stderr).replace('\\n', '\n'))

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
    logger.warning('area statistics file does not exist, synthesizing...')
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

    def __init__(self, expr, var_env, prec, file_name=None, dir=None):
        from ce.expr import Expr
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


def eval_expr(expr, var_env, prec):
    dir = tempfile.mktemp(suffix='/')
    f = CodeGenerator(expr, var_env, prec, dir=dir).generate()
    logger.debug('Synthesising', f)
    return xilinx(f, dir=dir)


if __name__ == '__main__':
    from ce.expr import Expr
    e = Expr('a + b + c')
    v = {'a': ['0', '1'], 'b': ['0', '100'], 'c': ['0', '100000']}
    logger.info(_para_synth(('add', 5, 10)))
    logger.info(e.area(v, 23))
    logger.info(eval_expr(e, v, 23))
    plot(load(default_file))
