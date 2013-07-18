import itertools

from matplotlib import rc, pyplot

import ce.logger as logger


def _analyser(expr_set, var_env, prec=None):
    from ce.analysis.core import AreaErrorAnalysis
    precs = [prec] if prec else None
    return AreaErrorAnalysis(expr_set, var_env, precs)


def analyse(expr_set, var_env, prec=None, vary_width=False):
    return _analyser(expr_set, var_env, prec).analyse()


def frontier(expr_set, var_env, prec=None, vary_width=None):
    return _analyser(expr_set, var_env, prec).frontier()


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


def expr_frontier(expr_set, var_env, prec=None):
    return expr_list(frontier(expr_set, var_env, prec))


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
    if not legend:
        return
    escapes = '# $ % & ~ \ _ ^ { }'.split(' ')
    new_legend = []
    for i, l in enumerate(legend.split('$')):
        if i % 2 == 0:
            for s in escapes:
                l = l.replace(s, '\%s' % s)
        new_legend.append(l)
    return '$'.join(new_legend)


class Plot(object):

    def __init__(self, result=None, var_env=None, depth=None, precs=None,
                 log=None, legend_pos=None, **kwargs):
        self.result_list = []
        self.legend_pos = legend_pos
        if result:
            self.add(result, **kwargs)
        self.var_env = var_env
        self.depth = depth
        self.precs = precs
        if not log is None:
            self.log_enable = log
        super().__init__()

    def add_analysis(self, expr, func=None, precs=None, var_env=None,
                     depth=None, annotate=False, legend=None,
                     legend_depth=False, legend_time=False, **kwargs):
        import time
        from ce.common import invalidate_cache
        var_env = var_env or self.var_env
        d = depth or self.depth
        precs = precs or self.precs or [None]
        results = []
        if legend_time:
            invalidate_cache()
        t = time.time()
        for p in precs:
            if p:
                logger.persistent('Precision', p)
            if func:
                derived = func(expr, var_env=var_env, depth=d, prec=p)
            else:
                derived = expr
            analysis_func = frontier if p else analyse
            r = analysis_func(derived, var_env, p)
            results += r
        t = time.time() - t
        if func:
            front = True
            marker = 'x'
        else:
            front = False
            marker = 'o'
        depth = d if legend_depth else None
        duration = t if legend_time else None
        kwargs.setdefault('marker', marker)
        logger.unpersistent('Precision')
        self.add(results, legend=legend, frontier=front, annotate=annotate,
                 time=duration, depth=depth, **kwargs)
        return self

    def add(self, result, expr=None,
            legend=None, frontier=True, annotate=False, time=None, depth=None,
            color_group=None, **kwargs):
        if not result:
            return
        if legend:
            if depth:
                legend += ', %d' % depth
            if time:
                legend += ' (%1.2fs)' % time
        self.result_list.append({
            'result': result,
            'legend': _escape_legend(legend),
            'frontier': frontier,
            'annotate': annotate,
            'color_group': color_group,
            'kwargs': kwargs
        })
        return self

    plot_defaults = {
        'alpha': 0.7,
        'linestyle': '-',
        'linewidth': 1.0,
    }

    plot_forbidden = ['marker', 'facecolors', 's']

    scatter_defaults = {
        's': 100,
    }

    scatter_forbidden = ['linestyle']

    def _colors(self):
        return itertools.cycle('bgrcmyk')

    def _markers(self):
        return itertools.cycle('so+x.v^<>')

    def _auto_scale(self, plot, xlim, ylim):
        try:
            log_enable = self.log_enable
        except AttributeError:
            log_enable = False
            if min(ylim) <= 0:
                log_enable = True
            elif max(ylim) / min(ylim) >= 10:
                log_enable = True
            self.log_enable = log_enable
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
        plot.locator_params(axis='x', nbins=7)

    def _plot(self):
        from ce.analysis.core import AreaErrorAnalysis, pareto_frontier_2d
        try:
            return self.figure
        except AttributeError:
            pass
        self.figure = pyplot.figure()
        plot = self.figure.add_subplot(111)
        colors = self._colors()
        color_groups = {}
        for d in self.result_list:
            if d['color_group'] is None:
                continue
            color_groups[d['color_group']] = next(colors)
        markers = self._markers()
        ymin, ymax = float('Inf'), float('-Inf')
        for r in self.result_list:
            kwargs = dict(self.plot_defaults)
            kwargs.update(r['kwargs'])
            if not r['color_group'] is None:
                kwargs['color'] = color_groups[r['color_group']]
            elif not 'color' in kwargs:
                kwargs['color'] = next(colors)
            if not 'marker' in kwargs:
                kwargs['marker'] = next(markers)
            area, error = zip_result(r['result'])
            ymin, ymax = min(ymin, min(error)), max(ymax, max(error))
            scatter_kwargs = dict(self.scatter_defaults)
            scatter_kwargs.update(kwargs)
            for k in self.scatter_forbidden:
                if k in scatter_kwargs:
                    del scatter_kwargs[k]
            plot.scatter(area, error, label=r['legend'], **scatter_kwargs)
            r['kwargs'] = kwargs
        xlim = plot.get_xlim()
        for r in self.result_list:
            if r['frontier']:
                kwargs = r['kwargs']
                kwargs['marker'] = None
                for k in self.plot_forbidden:
                    if k in kwargs:
                        del kwargs[k]
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
        legend_pos = self.legend_pos or (1.1, 1.1)
        l = plot.legend(
            bbox_to_anchor=legend_pos, ncol=1,
            fontsize='small', scatterpoints=1, columnspacing=0,
            labelspacing=0.1, handlelength=0.5, handletextpad=0.3,
            borderpad=0.3)
        if l:
            l.draggable()
        plot.grid(True, which='both', ls=':')
        plot.set_xlabel('Area (Number of LUTs)')
        plot.set_ylabel('Absolute Error')
        return self.figure

    def show(self):
        logger.info('Showing plot')
        self._plot()
        pyplot.show()

    def save(self, *args, **kwargs):
        self._plot().savefig(*args, bbox_inches='tight', **kwargs)


def plot(result, **kwargs):
    p = Plot(result, **kwargs)
    p.show()
    return p


def analyse_and_plot(s, v, d=None, f=None, o=False, t=True):
    from ce.transformer.utils import greedy_trace
    f = f or [greedy_trace]
    p = Plot(var_env=v, depth=d)
    try:
        for i, (d, m) in enumerate(itertools.product(s, f)):
            e, depth, legend = d['e'], d.get('d'), d.get('l')
            if len(f) > 1:
                fname = '%s' % m.__name__
                if not legend:
                    legend = fname
                else:
                    legend += ', ' + fname
            logger.info('Expr', e, 'Label', legend)
            p.add_analysis(e, func=m, depth=depth, legend=legend, marker='+',
                           color_group=i, legend_time=t)
            if o:
                legend += ' original'
                p.add_analysis(e, legend=legend, marker='o', color_group=i)
    except KeyboardInterrupt:
        pass
    return p


rc('font', family='serif', size=24, serif='Times')
rc('text', usetex=True)


if __name__ == '__main__':
    logger.set_context(level=logger.levels.info)
    p = Plot(var_env={'x': [0, 1]})
    p.add_analysis('x * x + x + 1', legend='1')
    p.add_analysis('x * (x + 1) + 1', legend='2')
    p.add_analysis('1 + x + x * x', legend='3')
    p.show()
