import os
import pickle

from soap import logger
from soap.context import context
from soap.shell.utils import optimize, emir2csv

logger.set_context(level=logger.levels.debug)


def _optimize(source, name):
    emir_name = name + '.emir'
    if os.path.exists(emir_name):
        with open(emir_name, 'rb') as f:
            return pickle.load(f)
    try:
        emir = optimize(source, name)
    except Exception as e:
        logger.error(e)
        emir = None
    else:
        with open(emir_name, 'wb') as f:
            pickle.dump(emir, f)
    return emir


def _csv(emir, name):
    csv_name = name + '.csv'
    if os.path.exists(csv_name):
        return
    with open(csv_name, 'w') as f:
        try:
            emir2csv(emir, f)
        except Exception as e:
            logger.error(e)


def main():
    name_base = 'examples/{}.soap'
    file_params = [
        ('2mm', {'unroll_depth': 8, 'fast_factor': 0.05}),
        ('3mm', {'unroll_depth': 10, 'fast_factor': 0.05}),
        ('atax', {'unroll_depth': 10, 'fast_factor': 0.05}),
        ('bicg', {'unroll_depth': 10, 'fast_factor': 0.05}),
        ('gemm', {'unroll_depth': 10, 'fast_factor': 0.05}),
        ('gemver', {'unroll_depth': 10, 'fast_factor': 0.05}),
        # ('gemsummv', {'unroll_depth': 10, 'fast_factor': 0.05}),
    ]
    for name, params in file_params:
        print('=' * 60)
        print(name)
        print('=' * 60)
        name = name_base.format(name)
        source = open(name, 'r').read()
        with context.local(**params):
            emir = _optimize(source, name)
        if emir:
            _csv(emir, name)


if __name__ == '__main__':
    main()
