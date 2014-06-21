import os

from soap import logger
from soap.common import timeit
from soap.expression import operators
from soap.flopoco.common import (
    flopoco, xilinx, default_file, we_range, wf_range
)


def _eval_operator(op, we, wf, f=None, dir=None):
    dir, f = flopoco(op, we, wf, f, dir)
    return dict(op=op, we=we, wf=wf, value=xilinx(f, dir))


@timeit
def _para_synth(op_we_wf):
    import sh
    op, we, wf = op_we_wf
    work_dir = 'syn_{}'.format(os.getpid())
    try:
        item = _eval_operator(op, we, wf, f=None, dir=work_dir)
        logger.info('Processed', item)
        return item
    except sh.ErrorReturnCode:
        logger.error('Error processing {}, {}, {}'.format(op, we, wf))


_pool_ = None


def _pool():
    global _pool_
    if _pool_ is None:
        import multiprocessing
        _pool_ = multiprocessing.Pool()
    return _pool_


@timeit
def _batch_synth(we_range, wf_range):
    import itertools
    args = itertools.product(['add', 'mul'], we_range, wf_range)
    return list(_pool().imap_unordered(_para_synth, args))


def _load(file_name):
    import pickle
    with open(file_name, 'rb') as f:
        return pickle.loads(f.read())


def _save(file_name, results):
    import pickle
    results = [i for i in results if not i is None]
    with open(file_name, 'wb') as f:
        pickle.dump(results, f)


def _plot(results):
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


class FlopocoMissingImplementationError(Exception):
    """Unsynthesizable operator"""


_loaded = False
_add = _mul = None


def _statistics_dictionaries():
    global _loaded, _add, _mul

    if _loaded:
        dictionaries = {
            operators.ADD_OP: _add,
            operators.SUBTRACT_OP: _add,
            operators.MULTIPLY_OP: _mul,
            operators.FIXPOINT_OP: 0,
        }
        return dictionaries

    _add = {}
    _mul = {}

    if not os.path.isfile(default_file):
        logger.error(
            'No flopoco statistics available, please consider regenerate.')

    for i in _load(default_file):
        xv, yv, zv = int(i['we']), int(i['wf']), int(i['value'])
        if i['op'] == 'add':
            _add[xv, yv] = zv
        elif i['op'] == 'mul':
            _mul[xv, yv] = zv

    _loaded = True
    return _statistics_dictionaries()


def operator_luts(op, we, wf):
    try:
        stats = _statistics_dictionaries()[op]
    except KeyError:
        logger.error('No statistics exist for operator {}'.format(op))
        return 0

    if isinstance(stats, int):
        return stats

    value = stats.get((we, wf))
    if value is not None:
        return value

    if wf not in wf_range:
        raise FlopocoMissingImplementationError(
            'Precision {} out of range'.format(wf))
    if we not in we_range:
        raise FlopocoMissingImplementationError(
            'Exponent width {} out of range'.format(we))
    return operator_luts(op, we + 1, wf)


def generate():
    logger.set_context(level=logger.levels.info)
    _save(default_file, _batch_synth(we_range, wf_range))
