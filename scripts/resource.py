import itertools
import os
import pickle
from glob import glob

from matplotlib import pyplot, rc

from soap.common.parallel import pool
from soap.context import context
from soap.semantics.functions.label import resources
from soap.shell.utils import parse, legup_and_quartus


rc('font', family='serif', size=15, serif='Times')
rc('text', usetex=True)

results_file_name = 'resources_compare_no_sharing.pkl'


def load_results():
    try:
        with open(results_file_name, 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        return []


def save_results(results):
    with open(results_file_name, 'wb') as f:
        pickle.dump(results, f)


def worker(args):
    i, n, name, r, iv, rv = args
    try:
        mir = r.expression
        print('Generating code...')
        code, legup_stats, quartus_stats, fmax = legup_and_quartus(mir, iv, rv)
        soap_stats = resources(mir, iv, rv, context.precision)
        result = {
            'soap_area': soap_stats,
            'legup_area': legup_stats,
            'quartus_area': quartus_stats,
            'quartus_fmax': fmax,
            'mir': r.expression,
            'name': name,
            'code': code,
        }
        print('{}/{}'.format(i + 1, n), result['soap_area'],
              result['legup_area'], result['quartus_area'],
              result['quartus_fmax'])
        return result
    except Exception as e:
        print(e)
        return


def compare(results):
    done_mirs = {r['mir'] for r in results}
    pool._cpu = 4

    for emir_file in glob('examples/*.emir'):
        print(emir_file)
        soap_file = os.path.splitext(emir_file)[0]
        with open(soap_file) as f:
            p, iv, rv = parse(f.read())
        with open(emir_file, 'rb') as f:
            emir = pickle.load(f)
            emir_results = [
                r for r in emir['results'] if r.expression not in done_mirs]
            emir_results = sorted(emir_results, key=lambda r: r.area)
            n = len(emir_results)
            arg_list = [(i, n, emir_file, r, iv, rv)
                        for i, r in enumerate(emir_results)]
            new_results = pool.map_unordered(worker, arg_list)
            results += [r for r in new_results if r is not None]
    return results


def data_points(results):
    return [(r['soap_area'].lut, r['legup_area'].lut,
             r['quartus_area'].lut) for r in results]


def plot_scatter(results):
    from scipy import stats
    points = data_points(results)
    soap, legup, quartus = zip(*points)
    k, m, r, p, e = stats.linregress(soap, quartus)
    print(k, m, r, p, e)
    m = 0
    k = sum(quartus) / sum(soap)
    print(k)
    figure = pyplot.figure()
    plot = figure.add_subplot(111)
    plot.scatter(soap, quartus, label='Quartus', marker='.', color='b')
    plot.plot([0, max(soap)], [m, k * max(soap) + m])
    plot.set_xlim(0, max(soap))
    plot.set_ylim(0, max(quartus))
    # plot.scatter(soap, legup, label='LegUp', marker='x', color='r')
    plot.set_xlabel('Estimated (No of LUTs)')
    plot.set_ylabel('Actual (No of LUTs)')
    # plot.legend(bbox_to_anchor=(0.4, 1.0), fontsize='small', scatterpoints=1)
    figure.savefig('resource.pdf')
    pyplot.show()


def plot_percentage_difference(results):
    points = data_points(results)
    xdiffs, ydiffs = [], []
    for a, b in itertools.product(points, points):
        if a[0] <= b[0]:
            continue
        xdiffs.append(abs(a[0] - b[0]) / max(a[0], b[0]) * 100)
        ydiffs.append(abs(a[2] - b[2]) / max(a[2], b[2]) * 100)
    figure = pyplot.figure()
    plot = figure.add_subplot(111)
    plot.scatter(xdiffs, ydiffs, marker='.', color='k')
    plot.set_xlabel('Percentage difference of Estimated LUTs')
    plot.set_ylabel('Percentage difference of Acutal LUTs')
    figure.savefig('resource_diff.pdf')
    pyplot.show()


def plot_order(results):
    points = sorted(data_points(results))
    soap, legup, quartus = zip(*points)
    old_quartus = quartus
    quartus = sorted(range(len(quartus)), key=lambda i: (quartus[i], soap[i]))
    soap = sorted(range(len(soap)), key=lambda i: (soap[i], old_quartus[i]))
    legup = sorted(range(len(legup)), key=lambda i: (legup[i], old_quartus[i]))
    figure = pyplot.figure(figsize=(4,3))
    plot = figure.add_subplot(111)
    # plot.scatter(soap, legup, label='LegUp', marker='x', color='r')
    plot.plot([0, max(soap)], [0, max(soap)], color='k')
    plot.scatter(soap, quartus, label='Quartus', marker='+', color='b')
    plot.set_xlabel('Rank of Actual LUTs')
    plot.set_ylabel('Rank of Estimated LUTs')
    plot.set_xlim(0, max(soap))
    plot.set_ylim(0, max(quartus))
    # plot.legend(bbox_to_anchor=(0.4, 1.0), fontsize='small', scatterpoints=1)
    figure.savefig('resource_rank.pdf', bbox_inches='tight', pad_inches=2)
    pyplot.show()


def plot_fmax():
    with open('resources_compare_sharing.pkl', 'rb') as f:
        sharing = pickle.load(f)
    with open('resources_compare_no_sharing.pkl', 'rb') as f:
        no_sharing = pickle.load(f)

    def get_fmax_list(l):
        return [r['quartus_fmax'] for r in l]

    sharing = sorted(sharing, key=lambda r: r['mir'])
    no_sharing = sorted(no_sharing, key=lambda r: r['mir'])

    imps = [(b['quartus_fmax'] - a['quartus_fmax']) / a['quartus_fmax']
            for a, b in zip(sharing, no_sharing)]
    imps_avg = sum(imps) / len(imps) * 100
    print(imps_avg)

    figure = pyplot.figure()
    plot = figure.add_subplot(111)
    plot.scatter(get_fmax_list(sharing), get_fmax_list(no_sharing), marker='+')
    figure.savefig('fmax.pdf')


def main():
    try:
        results = load_results()
        if not results:
            results = []
        results = compare(results)
    except KeyboardInterrupt:
        pass
    finally:
        print('Saving results...')
        save_results(results)
        return results


if __name__ == '__main__':
    # results = main()
    results = load_results()
    plot_scatter(results)
    # plot_percentage_difference(results)
    plot_order(results)
    # plot_fmax()
