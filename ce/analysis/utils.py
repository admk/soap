import itertools

from matplotlib import pyplot

from ce.analysis.core import AreaErrorAnalysis, pareto_frontier_2d


def analyse(expr_set, var_env):
    return AreaErrorAnalysis(expr_set, var_env).analyse()


def frontier(expr_set, var_env):
    return AreaErrorAnalysis(expr_set, var_env).frontier()


def list_from_keys(result, keys=None):
    if not isinstance(keys, str):
        try:
            return [[r[k] for k in keys or result[0].keys()] for r in result]
        except TypeError:
            pass
    return [r[keys] for r in result]


def zip_from_keys(result, keys='expression'):
    return zip(*list_from_keys(result, keys))


def zip_result(result):
    return zip_from_keys(result, keys=AreaErrorAnalysis.names())


def expr_list(result):
    return list_from_keys(result, keys='expression')


def expr_set(result):
    return set(expr_list(result))


def expr_frontier(expr_set, var_env):
    return expr_list(frontier(expr_set, var_env))


class Plot(object):

    def __init__(self, result=None, **kwargs):
        self.result_list = []
        if result:
            self.add(result, **kwargs)
        super().__init__()

    def add(self, result,
            legend=None, frontier=True, annotate=True, **kwargs):
        self.result_list.append({
            'result': result,
            'legend': legend,
            'frontier': frontier,
            'annotate': annotate,
            'kwargs': kwargs
        })

    plot_defaults = {
        'marker': 'o',
        'alpha': 0.7
    }

    def _colors(self, length):
        color_index = [float(i) / length for i in range(length)]
        return itertools.cycle(pyplot.cm.rainbow_r(color_index))

    def _plot(self):
        try:
            return self.figure
        except AttributeError:
            pass
        self.figure = pyplot.figure()
        plot = self.figure.add_subplot(111)
        ymin = ymax = None
        colors = self._colors(len(self.result_list))
        for i, r in enumerate(self.result_list):
            kwargs = dict(self.plot_defaults)
            kwargs.update(r['kwargs'])
            if not 'color' in kwargs:
                kwargs['color'] = next(colors)
            area, error = zip_result(r['result'])
            plot.scatter(area, error, label=r['legend'], **kwargs)
            emin, emax = min(error), max(error)
            if ymin is None:
                ymin, ymax = emin, emax
            else:
                ymin, ymax = min(ymin, emin), max(ymax, emax)
            if r['frontier']:
                keys = AreaErrorAnalysis.names()
                f = pareto_frontier_2d(r['result'], keys=keys)
                keys.append('expression')
                area, error, expr = zip_from_keys(f, keys=keys)
                legend = r['legend'] + ' frontier' if r['legend'] else None
                plot.plot(area, error, label=legend, **kwargs)
                if r['annotate']:
                    for x, y, e in zip(area, error, expr):
                        plot.annotate(str(e), xy=(x, y), alpha=0.5)
        plot.set_ylim(0.95 * ymin, 1.05 * ymax)
        plot.set_ymargin(0)
        plot.legend(loc='upper center', bbox_to_anchor=(0.5, 1.05), ncol=3)
        plot.set_xlabel('Area (Number of LUTs)')
        plot.set_ylabel('Absolute Error')
        return self.figure

    def show(self):
        self._plot()
        pyplot.show()

    def save(self, *args, **kwargs):
        self._plot().savefig(*args, **kwargs)


def plot(result):
    Plot(result).show()
