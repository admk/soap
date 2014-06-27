import os
import tempfile
from contextlib import contextmanager

from soap import logger
from soap.expression.operators import (
    ADD_OP, SUBTRACT_OP, MULTIPLY_OP, DIVIDE_OP
)


flopoco_operators = ['FPAdder', 'FPMultiplier', 'FPDiv']
operators_map = {
    ADD_OP: 'FPAdder',
    SUBTRACT_OP: 'FPAdder',
    MULTIPLY_OP: 'FPMultiplier',
    DIVIDE_OP: 'FPDiv',
}

we_min, we_max = 5, 15
wf_min, wf_max = 10, 112
we_range = list(range(we_min, we_max + 1))
wf_range = list(range(wf_min, wf_max + 1))

directory = 'soap/flopoco/'
default_file = directory + 'luts.pkl'
template_file = directory + 'template.vhdl'

device_name = 'Virtex6'
device_model = 'xc6vlx760'


@contextmanager
def cd(d):
    import sh
    p = os.path.abspath(os.curdir)
    if d:
        sh.mkdir('-p', d)
        sh.cd(d)
    try:
        yield
    except Exception:
        raise
    finally:
        sh.cd(p)


def get_luts(file_name):
    from bs4 import BeautifulSoup
    with open(file_name, 'r') as f:
        f = BeautifulSoup(f.read())
        app = f.document.application
        util = app.find('section', stringid='XST_DEVICE_UTILIZATION_SUMMARY')
        luts = util.find('item', stringid='XST_NUMBER_OF_SLICE_LUTS')
        return int(luts.get('value'))


def flopoco(op, we, wf, f=None, dir=None):
    import sh
    from soap.expression import ADD_OP, MULTIPLY_OP
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
        logger.debug('Flopoco', flopoco_cmd)
        sh.flopoco(*flopoco_cmd)
        try:
            with open(f) as fh:
                if not fh.read():
                    raise IOError()
        except (IOError, FileNotFoundError):
            logger.error('Flopoco failed to generate file %s' % f)
            raise
    return dir, f


def xilinx(f, dir=None):
    import sh
    file_base = os.path.split(f)[1]
    file_base = os.path.splitext(file_base)[0]
    g = file_base + '.ngc'
    cmd = ['run', '-p', device_model]
    cmd += ['-ifn', f, '-ifmt', 'VHDL']
    cmd += ['-ofn', g, '-ofmt', 'NGC']
    dir = dir or tempfile.mktemp(suffix='/')
    with cd(dir):
        logger.debug('Xilinx', repr(cmd))
        sh.xst(sh.echo(*cmd), _out='out.log', _err='err.log')
        return get_luts(file_base + '.ngc_xst.xrpt')
