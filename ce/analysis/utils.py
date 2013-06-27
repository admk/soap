import itertools

from matplotlib import rc, pyplot


def _analyser(vary_width):
    if vary_width:
        from ce.analysis.core import VaryWidthAnalysis
        return VaryWidthAnalysis
    from ce.analysis.core import AreaErrorAnalysis
    return AreaErrorAnalysis


def analyse(expr_set, var_env, vary_width=False):
    return _analyser(vary_width)(expr_set, var_env).analyse()


def frontier(expr_set, var_env, analyser=None):
    return _analyser(analyser)(expr_set, var_env).frontier()


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
    from ce.analysis.core import AreaErrorAnalysis
    return zip_from_keys(result, keys=AreaErrorAnalysis.names())


def expr_list(result):
    return list_from_keys(result, keys='expression')


def expr_set(result):
    return set(expr_list(result))


def expr_frontier(expr_set, var_env):
    return expr_list(frontier(expr_set, var_env))


_ZIGZAG_MARGIN = 100.0


def _insert_region_frontier(sx, sy):
    lx = []
    ly = []
    py = sy[0] * _ZIGZAG_MARGIN
    for x, y in zip(sx, sy):
        lx.append(x)
        ly.append(py)
        lx.append(x)
        ly.append(y)
        py = y
    lx.append(sx[-1] * _ZIGZAG_MARGIN)
    ly.append(py)
    return lx, ly


def _escape_legend(legend):
    escapes = '# $ % & ~ \ _ ^ { }'.split(' ')
    new_legend = []
    for i, l in enumerate(legend.split('$')):
        if i % 2 == 0:
            for s in escapes:
                l = l.replace(s, '\%s' % s)
        new_legend.append(l)
    return '$'.join(new_legend)


class Plot(object):

    def __init__(self, result=None, **kwargs):
        self.result_list = []
        if result:
            self.add(result, **kwargs)
        super().__init__()

    def add(self, result,
            legend=None, frontier=True, annotate=False, **kwargs):
        self.result_list.append({
            'result': result,
            'legend': _escape_legend(legend),
            'frontier': frontier,
            'annotate': annotate,
            'kwargs': kwargs
        })

    plot_defaults = {
        'alpha': 0.7,
    }

    def _colors(self, length):
        return itertools.cycle('bgrcmyk')

    def _markers(self):
        return itertools.cycle('so+x.v^<>')

    def _auto_scale(self, plot, xlim, ylim):
        log_enable = False
        if min(ylim) <= 0:
            log_enable = True
        elif max(ylim) / min(ylim) >= 10:
            log_enable = True
        if log_enable:
            plot.set_yscale('log')
            plot.set_ylim(ylim)
        else:
            plot.set_yscale('linear')
            ymin, ymax = ylim
            ymar = 0.1 * (ymax - ymin)
            plot.set_ylim(ymin - ymar, ymax + ymar)
            plot.yaxis.get_major_formatter().set_scientific(True)
            plot.yaxis.get_major_formatter().set_powerlimits((-3, 4))
        plot.set_xlim(max(min(xlim), 0), max(xlim))

    def _plot(self):
        from ce.analysis.core import AreaErrorAnalysis, pareto_frontier_2d
        try:
            return self.figure
        except AttributeError:
            pass
        self.figure = pyplot.figure()
        plot = self.figure.add_subplot(111)
        colors = self._colors(len(self.result_list))
        markers = self._markers()
        ymin, ymax = float('Inf'), float('-Inf')
        for r in self.result_list:
            kwargs = dict(self.plot_defaults)
            kwargs.update(r['kwargs'])
            if not 'color' in kwargs:
                kwargs['color'] = next(colors)
            if not 'marker' in kwargs:
                kwargs['marker'] = next(markers)
            area, error = zip_result(r['result'])
            ymin, ymax = min(ymin, min(error)), max(ymax, max(error))
            plot.scatter(area, error,
                         label=r['legend'],
                         **dict(kwargs, linestyle='-', linewidth=1, s=20))
            r['kwargs'] = kwargs
        xlim = plot.get_xlim()
        for r in self.result_list:
            if r['frontier']:
                kwargs = r['kwargs']
                kwargs['marker'] = None
                keys = AreaErrorAnalysis.names()
                f = pareto_frontier_2d(r['result'], keys=keys)
                keys.append('expression')
                area, error, expr = zip_from_keys(f, keys=keys)
                lx, ly = _insert_region_frontier(area, error)
                plot.plot(lx, ly, **kwargs)
                plot.fill_between(lx, ly, max(ly),
                                  alpha=0.1, color=kwargs['color'])
                if r['annotate']:
                    for x, y, e in zip(area, error, expr):
                        plot.annotate(str(e), xy=(x, y), alpha=0.5)
        self._auto_scale(plot, xlim, (ymin, ymax))
        plot.legend(bbox_to_anchor=(1.1, 1.1), ncol=1)
        plot.grid(True, which='both', ls=':')
        plot.set_xlabel('Area (Number of LUTs)')
        plot.set_ylabel('Absolute Error')
        return self.figure

    def show(self):
        self._plot()
        pyplot.show()

    def save(self, *args, **kwargs):
        self._plot().savefig(*args, **kwargs)


def plot(result, **kwargs):
    p = Plot(result, **kwargs)
    p.show()
    return p


rc('font', family='serif', serif='Times')
rc('text', usetex=True)
