import os
import pickle
import re
import shutil
import tempfile
from glob import glob

import sh
from matplotlib import pyplot
from akpytemp.utils import code_gobble

from soap.context import context
from soap.flopoco.common import cd
from soap.program.generator.c import generate_function
from soap.semantics.functions.label import resources
from soap.semantics.label import s
from soap.shell.utils import parse


def wrap_in_main(iv, func):
    code = code_gobble(
        """
        {}

        int main() {{
            float rv = func({});
            return 0;
        }}
        """).format(func, ', '.join('1' for _ in iv))
    return code


legup_path = os.path.expanduser('~/legup/examples')

makefile = code_gobble(
    """
    NAME=test
    FAMILY=StratixIV
    NO_OPT=1
    NO_INLINE=1
    LEVEL={}
    include $(LEVEL)/Makefile.common
    """).format(legup_path)


def get_stats():
    with open('resources.legup.rpt') as f:
        file = f.read()
    dsp = int(re.search('DSP Elements: (\d+)', file).groups()[0])
    ff = int(re.search('Registers: (\d+)', file).groups()[0])
    lut = int(re.search('Combinational: (\d+)', file).groups()[0])
    return s(dsp, ff, lut)


def legup(code):
    d = tempfile.mktemp(suffix='/')
    try:
        with cd(d):
            with open('test.c', 'w') as f:
                f.write(code)
            with open('Makefile', 'w') as f:
                f.write(makefile)
            sh.make(_out='make.log', _err='make.err.log')
            stats = get_stats()
    except sh.ErrorReturnCode:
        raise
    else:
        return stats
    finally:
        shutil.rmtree(d)


results_file_name = 'resources_compare.pkl'


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

    for emir in glob('examples/*.emir'):
        print(emir)
        soap_file = os.path.splitext(emir)[0]
        with open(soap_file) as f:
            p, iv, rv = parse(f.read())
        with open(emir, 'rb') as f:
            emir = pickle.load(f)
            emir_results = [
                r for r in emir['results'] if r.expression not in done_mirs]
            n = len(emir_results)
            for i, r in enumerate(emir_results):
                try:
                    mir = r.expression
                    func = generate_function(mir, iv, rv, 'func')
                    code = wrap_in_main(iv, func)
                    legup_stats = legup(code)
                    soap_stats = resources(mir, iv, rv, context.precision)
                except Exception as e:
                    print(e)
                    continue
                results.append({
                    'soap_area': soap_stats,
                    'legup_area': legup_stats,
                    'mir': r.expression,
                    'code': code,
                })
                print('{}/{}'.format(i + 1, n), soap_stats, legup_stats)
    return results


def data_points(results):
    return [(r['soap_area'].lut, r['legup_area'].lut) for r in results]


def plot(results):
    print('Plotting...')
    points = data_points(results)
    soap, legup = zip(*points)
    figure = pyplot.figure()
    plot = figure.add_subplot(111)
    plot.scatter(soap, legup)
    pyplot.show()
    figure.savefig('resource.pdf')


def main():
    try:
        results = load_results()
        results = compare(results)
    except KeyboardInterrupt:
        pass
    finally:
        print('Saving results...')
        save_results(results)
    plot(results)


if __name__ == '__main__':
    main()
