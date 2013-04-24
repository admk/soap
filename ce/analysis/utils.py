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

    def __init__(self, result=None, legend=None):
        self.result_list = []
        if result:
            self.add(result, legend)
        super().__init__()

    def add(self, result, legend=None, frontier=True):
        self.result_list.append({
            'result': result,
            'legend': legend,
            'frontier': frontier,
        })

    def _plot(self):
        try:
            return self.figure
        except AttributeError:
            pass
        self.figure = pyplot.figure()
        plot = self.figure.add_subplot(111)
        ymin = ymax = None
        for r in self.result_list:
            area, error = zip_result(r['result'])
            plot.scatter(area, error, label=r['legend'])
            emin, emax = min(error), max(error)
            if ymin is None:
                ymin, ymax = emin, emax
            else:
                ymin, ymax = min(ymin, emin), max(ymax, emax)
            if r['frontier']:
                f = pareto_frontier_2d(
                    r['result'], keys=AreaErrorAnalysis.names())
                area, error = zip_result(f)
                legend = r['legend'] + ' frontier' if r['legend'] else None
                plot.plot(area, error, label=legend)
        plot.set_ylim(0.9 * ymin, 1.1 * ymax)
        plot.legend()
        return self.figure

    def show(self):
        self._plot()
        pyplot.show()

    def save(self, *args, **kwargs):
        self._plot().savefig(*args, **kwargs)


def plot(result):
    Plot(result).show()
