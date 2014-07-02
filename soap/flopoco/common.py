import os
import tempfile
from contextlib import contextmanager

from soap import logger
from soap.expression import operators


flopoco_command_map = {
    'IntAdder': ('{wi}', ),
    'IntMultiplier': ('{wi}', '{wi}', '{wi}', '1', '1', '0'),
    'FPAdder': ('{we}', '{wf}'),
    'FPMultiplier': ('{we}', '{wf}', '{wf}'),
    'FPSquarer': ('{we}', '{wf}', '{wf}'),
    'FPDiv': ('{we}', '{wf}'),
    'FPPow': ('{we}', '{wf}'),
    'FPExp': ('{we}', '{wf}'),
    'FPLog': ('{we}', '{wf}', '0'),
}
flopoco_operators = tuple(flopoco_command_map)
operators_map = {
    operators.ADD_OP: 'FPAdder',
    operators.SUBTRACT_OP: 'FPAdder',
    operators.MULTIPLY_OP: 'FPMultiplier',
    operators.DIVIDE_OP: 'FPDiv',
    operators.LESS_OP: 'FPAdder',
    operators.LESS_EQUAL_OP: 'FPAdder',
    operators.GREATER_OP: 'FPAdder',
    operators.GREATER_EQUAL_OP: 'FPAdder',
    operators.EQUAL_OP: 'FPAdder',
    operators.NOT_EQUAL_OP: 'FPAdder',
    operators.TERNARY_SELECT_OP: 'Multiplexer',
    operators.FIXPOINT_OP: 'Null',
    operators.UNARY_SUBTRACT_OP: 'OneLUT',
}

we_min, we_max = 5, 15
we_range = list(range(we_min, we_max + 1))

wf_min, wf_max = 10, 112
wf_range = list(range(wf_min, wf_max + 1))

wi_min, wi_max = 1, 100
wi_range = list(range(wi_min, wi_max + 1))

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


def flopoco_key(fop, we=-1, wf=-1, wi=-1):
    try:
        format_tuple = flopoco_command_map[fop]
    except KeyError:
        raise ValueError('Unrecognised operator {}'.format(fop))
    args = [fop]
    args += [a.format(we=we, wf=wf, wi=wi) for a in format_tuple]
    return tuple(args)


def flopoco(key, file_name=None, dir_name=None):
    import sh

    file_name = file_name or tempfile.mktemp(suffix='.vhdl', dir='')
    cmd = ('-target=' + device_name, '-outputfile=' + file_name) + key
    logger.debug('flopoco: {!r}'.format(cmd))

    dir_name = dir_name or tempfile.mktemp(suffix='/')

    with cd(dir_name):
        sh.flopoco(*cmd)
        try:
            with open(file_name) as fh:
                if not fh.read():
                    raise IOError()
        except (IOError, FileNotFoundError):
            logger.error('Flopoco failed to generate file ' + file_name)
            raise

    return file_name, dir_name


def get_luts(file_name):
    from bs4 import BeautifulSoup
    with open(file_name, 'r') as f:
        f = BeautifulSoup(f.read())
        app = f.document.application
        util = app.find('section', stringid='XST_DEVICE_UTILIZATION_SUMMARY')
        luts = util.find('item', stringid='XST_NUMBER_OF_SLICE_LUTS')
        if luts:
            return int(luts.get('value'))
        logger.warning('{} requires no LUTs'.format(file_name))
        return 0


def xilinx(file_name, dir_name=None):
    import sh

    file_base = os.path.split(file_name)[1]
    file_base = os.path.splitext(file_base)[0]
    synth_name = file_base + '.ngc'

    cmd = ['run', '-p', device_model]
    cmd += ['-ifn', file_name, '-ifmt', 'VHDL']
    cmd += ['-ofn', synth_name, '-ofmt', 'NGC']
    logger.debug('xst: {!r}'.format(cmd))

    dir_name = dir_name or tempfile.mktemp(suffix='/')
    with cd(dir_name):
        out_file_name = file_base + '.out.log'
        err_file_name = file_base + '.err.log'

        sh.xst(sh.echo(*cmd), _out=out_file_name, _err=err_file_name)

        return get_luts(file_base + '.ngc_xst.xrpt')
