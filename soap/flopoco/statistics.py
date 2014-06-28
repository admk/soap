import itertools
import os
import pickle

from soap import logger
from soap.common import timeit
from soap.flopoco.common import (
    flopoco_operators, operators_map, we_range, wf_range, wi_range,
    flopoco_key, flopoco, xilinx, default_file
)


INVALID = -1


def _eval_operator(key, dir_name=None):
    file_name, dir_name = flopoco(key)
    return xilinx(file_name, dir_name)


@timeit
def _para_synth(key):
    import sh
    work_dir_name = 'syn_{}'.format(os.getpid())
    try:
        value = _eval_operator(key, dir_name=work_dir_name)
        logger.info('Processed {}, LUTs {}'.format(key, value))
        return key, value
    except sh.ErrorReturnCode:
        logger.error('Error processing {}'.format(key))
        return key, INVALID


_pool_ = None


def _pool():
    global _pool_
    if _pool_ is None:
        import multiprocessing
        _pool_ = multiprocessing.Pool()
    return _pool_


@timeit
def _batch_synth(we_range, wf_range, existing_results=None):
    existing_results = existing_results or {}

    logger.info('Generating synthesis schedule...')
    iterator = itertools.product(
        flopoco_operators, we_range, wf_range, wi_range)
    key_list = []
    for key in iterator:
        key = flopoco_key(*key)
        if key in existing_results:
            continue
        if key in key_list:
            continue
        key_list.append(key)

    logger.info('Synthesizing...')
    results = _pool().imap_unordered(_para_synth, key_list)
    results_dict = dict(existing_results)
    for r in results:
        key, value = r
        results_dict[key] = value

    logger.info('Synthesis complete')
    return results_dict


def _load(file_name):
    with open(file_name, 'rb') as f:
        return pickle.load(f)


def _save(file_name, results):
    with open(file_name, 'wb') as f:
        pickle.dump(results, f)


def _plot(results):
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    fig = plt.figure()
    ax = Axes3D(fig)
    vl = []
    for key, value in results.items():
        op, xv, yv = key
        zv = value
        if zv < 0:
            continue
        vl.append((xv, yv, zv))
    ax.scatter(*zip(*vl))
    plt.show()


class FlopocoMissingImplementationError(Exception):
    """Unsynthesizable operator"""


_stats = None


def operator_luts(op, we=None, wf=None, wi=None):
    global _stats
    if not _stats:
        if not os.path.isfile(default_file):
            logger.error(
                'No flopoco statistics available, please consider regenerate.')
        _stats = _load(default_file)

    fop = operators_map.get(op)
    value = _stats.get(flopoco_key(fop, we, wf, wi), INVALID)
    if value != INVALID:
        return value

    if fop not in flopoco_operators:
        raise FlopocoMissingImplementationError(
            'Operator {} has no statistics'.format(op))
    if wf not in wf_range:
        raise FlopocoMissingImplementationError(
            'Precision {} out of range'.format(wf))
    if we > max(we_range):
        raise FlopocoMissingImplementationError(
            'Exponent width {} out of range'.format(we))
    try:
        return operator_luts(op, we + 1, wf)
    except FlopocoMissingImplementationError:
        raise FlopocoMissingImplementationError(
            'Failed to get statistics for operator {} with exponent and '
            'mantissa widths {}, {}'.format(op, we, wf))


def generate():
    logger.set_context(level=logger.levels.info)
    existing_results = _load(default_file)
    _save(default_file, _batch_synth(we_range, wf_range, existing_results))
