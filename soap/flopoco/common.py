import math
import os
import tempfile
from contextlib import contextmanager

from soap import logger
from soap.common.cache import cached
from soap.expression import operators, OutputVariableTuple
from soap.semantics.error import IntegerInterval, ErrorSemantics


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
    operators.ADD_OP: ['FPAdder', 'IntAdder'],
    operators.SUBTRACT_OP: ['FPAdder', 'IntAdder'],
    operators.MULTIPLY_OP: ['FPMultiplier', 'IntMultiplier'],
    operators.DIVIDE_OP: 'FPDiv',
    operators.LESS_OP: ['FPAdder', 'IntAdder'],
    operators.LESS_EQUAL_OP: ['FPAdder', 'IntAdder'],
    operators.GREATER_OP: ['FPAdder', 'IntAdder'],
    operators.GREATER_EQUAL_OP: ['FPAdder', 'IntAdder'],
    operators.EQUAL_OP: ['FPAdder', 'IntAdder'],
    operators.NOT_EQUAL_OP: ['FPAdder', 'IntAdder'],
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

directory = os.path.dirname(__file__)
default_file = os.path.join(directory, 'luts.pkl')
template_file = os.path.join(directory, 'template.vhdl')

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


_FILTER_OPERATORS = operators.TRADITIONAL_OPERATORS + [
    operators.TERNARY_SELECT_OP
]


@cached
def _datatype_exponent(op, label):
    if isinstance(label, OutputVariableTuple):
        exponent = 0
        for l in label:
            label_datatype, label_exponent = _datatype_exponent(op, l)
            exponent += label_exponent
        return None, exponent

    if op == operators.FIXPOINT_OP:
        return None, 0
    if op not in _FILTER_OPERATORS:
        return None, None

    bound = label.bound
    datatype = type(bound)

    if datatype is IntegerInterval:
        if bound.is_top():
            return datatype, flopoco.wi_max
        if bound.is_bottom():
            return datatype, flopoco.wi_min
        bound_max = max(abs(bound.min), abs(bound.max), 1)
        width_max = int(math.ceil(math.log(bound_max + 1, 2)) + 1)
        return datatype, width_max

    if datatype is ErrorSemantics:
        bound = bound.v
        if bound.is_top():
            return datatype, flopoco.we_max
        if bound.is_bottom():
            return datatype, flopoco.we_min
        bound_max = max(abs(bound.min), abs(bound.max), 1)
        try:
            exp_max = math.floor(math.log(bound_max, 2))
        except OverflowError:
            return datatype, flopoco.we_max
        try:
            exponent = int(math.ceil(math.log(exp_max + 1, 2) + 1))
            return datatype, max(exponent, flopoco.we_min)
        except ValueError:
            return datatype, flopoco.we_min

    raise TypeError('Unrecognized type of bound {!r}'.format(bound))
