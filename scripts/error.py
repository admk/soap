import os
import pickle
from glob import glob

from soap import logger
from soap.shell.utils import parse, _generate_samples, _run_simulation

logger.set_context(level=logger.levels.info)
population_size = 200
results_file_name = 'error_compare.pkl'


def load_results():
    try:
        with open(results_file_name, 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        return []


def save_results(results):
    with open(results_file_name, 'wb') as f:
        pickle.dump(results, f)


def compare(results):
    done_mirs = {r['mir'] for r in results}

    for emir_file in glob('examples/*.emir'):
        print(emir_file)
        soap_file = os.path.splitext(emir_file)[0]
        with open(soap_file) as f:
            p, iv, rv = parse(f.read())
        samples = _generate_samples(iv)
        with open(emir_file, 'rb') as f:
            emir = pickle.load(f)
            emir_results = [
                r for r in emir['results'] if r.expression not in done_mirs]
            emir_results = sorted(emir_results, key=lambda r: r.error)
            n = len(emir_results)
            for i, r in enumerate(emir_results):
                logger.persistent('MIR', '{}/{}'.format(i, n))
                error = _run_simulation(r.expression, samples, rv)
                result = {
                    'bound': r.error,
                    'simulation': error,
                    'mir': r.expression,
                    'name': emir_file,
                }
                logger.info('AE', r.error, 'SE', str(error))
                results.append(result)
                save_results(results)
    return results


def main():
    results = load_results()
    compare(results)
    save_results(results)


if __name__ == '__main__':
    main()
