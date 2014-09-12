"""
.. module:: soap.analysis.utils
    :synopsis: Provides utility functions for analysis and plotting.
"""
import math
import itertools

from soap import logger
from soap.analysis.core import Analysis
from soap.context import context


def analyze(expr_set, state, out_vars=None):
    """Provides area and error analysis of expressions with input ranges
    and precisions.

    :param expr_set: A set of expressions.
    :type expr_set: set or list
    :param state: The ranges of input variables.
    :type state: dictionary containing mappings from variables to
        :class:`soap.semantics.error.Interval`
    :param out_vars: The output variables of the metastate
    :type out_vars: :class:`collections.Sequence`
    """
    return Analysis(expr_set, state, out_vars).analyze()


def frontier(expr_set, state, out_vars=None):
    """Provides the Pareto frontier of the area and error analysis of
    expressions with input ranges and precisions.

    :param expr_set: A set of expressions.
    :type expr_set: set or list
    :param state: The ranges of input variables.
    :type state: dictionary containing mappings from variables to
        :class:`soap.semantics.error.Interval`
    :param out_vars: The output variables of the metastate
    :type out_vars: :class:`collections.Sequence`
    """
    return Analysis(expr_set, state, out_vars).frontier()


def thick_frontier(expr_set, state, out_vars=None):
    """Provides the thick Pareto frontier of the area and error analysis of
    expressions with input ranges and precisions.

    :param expr_set: A set of expressions.
    :type expr_set: set or list
    :param state: The ranges of input variables.
    :type state: dictionary containing mappings from variables to
        :class:`soap.semantics.error.Interval`
    :param out_vars: The output variables of the metastate
    :type out_vars: :class:`collections.Sequence`
    """
    return Analysis(expr_set, state, out_vars).thick_frontier()


_ZIGZAG_MARGIN = 1000.0
_SCATTER_MARGIN = 0.1


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
    escapes = '# $ % & ~ _ ^ { }'.split(' ')
    new_legend = []
    for i, l in enumerate(legend.split('$')):
        if i % 2 == 0:
            for s in escapes:
                l = l.replace(s, '\%s' % s)
        new_legend.append(l)
    return '$'.join(new_legend)


def _margin(lmin, lmax):
    margin = _SCATTER_MARGIN * (lmax - lmin)
    return lmin - margin, lmax + margin


def _linear_margin(lmin, lmax):
    lmin, lmax = _margin(lmin, lmax)
    return max(lmin, 0), lmax


def _log_margin(lmin, lmax):
    lmin, lmax = math.log10(lmin), math.log10(lmax)
    logger.info(lmin, lmax)
    lmin, lmax = _margin(lmin, lmax)
    return math.pow(10, lmin), math.pow(10, lmax)


class Plot(object):
    """Provides plotting of results"""
    def __init__(self, result=None, state=None, out_vars=None,
                 depth=None, precs=None, log=None, legend_pos=None, **kwargs):
        """Initialisation.

        :param result: results provided by :func:`analyze`.
        :type result: list
        :param state: The ranges of input variables to be used in transforms.
        :type state: dictionary containing mappings from variables to
            :class:`soap.semantics.error.Interval`
        :param depth: the depth limit used in transforms.
        :type depth: int
        :param precs: Precisions to be used to evaluate the expressions,
            defaults to single precision.
        :type precs: int or a list of int
        :param log: If set, force figure to log scale; if unset, then linear
            scale. If unspecified, then the class will automatically detect
            scaling based on the data.
        :type log: bool
        :param legend_pos: The position of the legend, `(x_pos, y_pos)`,
            automatic positioning in the upper right corner if unspecified.
        :type legend_pos: tuple
        """
        self.result_list = []
        self.legend_pos = legend_pos
        if result:
            self.add(result, **kwargs)
        self.state = state
        self.out_vars = out_vars
        self.depth = depth
        self.precs = precs
        if log is not None:
            self.log_enable = log
        super().__init__()

    def add_analysis(self, expr, func=None, precs=None,
                     out_vars=None, state=None,
                     depth=None, annotate=False, legend=None,
                     legend_depth=False, legend_time=False, **kwargs):
        """Performs transforms, then analyzes expressions and add results to
        plot.

        :param expr: original expression to be transformed.
        :type expr: :class:`soap.expression.Expr`
        :param func: the function used to transform `expr`.
        :type func: callable with arguments::
            `(tree, state, depth, prec)`, where `tree` is an expression,
            `state` is the input ranges, `depth` is the depth limit and
            `prec` is the precision used.
        :param precs: Precisions used to evaluate the expressions, defaults to
            single precision.
        :type precs: int or a list of int
        :param depth: the depth limit used in transforms.
        :type depth: int
        :param annotate: Annotates expressions on the Pareto frontier if set.
        :type annotate: bool
        :param legend: The legend name for the results.
        :type legend: str
        :param legend_depth: If set, will show depth limit on the legend.
        :type legend_depth: bool
        :param legend_time: If set, will show timing of transform on the
            legend.
        :type legend_time: bool
        """
        import time
        from soap.common import invalidate_cache
        state = state or self.state
        out_vars = out_vars or self.out_vars
        d = depth or self.depth
        precs = precs or self.precs
        analysis_func = frontier if len(precs) > 1 else analyze
        results = []
        if legend_time:
            invalidate_cache()
        t = time.time()
        for p in precs:
            if p:
                logger.persistent('Precision', p)
            if func:
                with context.local(precision=p, window_depth=d):
                    derived = func(expr, state, out_vars)
            else:
                derived = {expr}
            r = analysis_func(derived, state, out_vars)
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
        duration = duration if legend_time is True else legend_time
        kwargs.setdefault('marker', marker)
        logger.unpersistent('Precision')
        self.add(results, legend=legend, frontier=front, annotate=annotate,
                 time=duration, depth=depth, **kwargs)
        return self

    def add(self, result, expr=None,
            legend=None, frontier=True, annotate=False, time=None, depth=None,
            color_group=None, **kwargs):
        """Add analyzed results.

        :param expr: Optional, the original expression.
        :type expr: :class:`soap.expression.Expr`
        :param legend: The legend name for the results.
        :type legend: str
        :param frontier: If set, plots the frontier.
        :type frontier: bool
        :param annotate: Annotates expressions on the Pareto frontier if set.
        :type annotate: bool
        :param depth: If specifed, will show depth limit on the legend.
        :type depth: int
        :param time: If specified, will show timing on the legend.
        :type time: float
        """
        if legend:
            if depth:
                legend += ', %d' % depth
            if time:
                try:
                    legend += ' (%1.2fs)' % time
                except TypeError:
                    legend += ' (%s)' % time
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

    plot_forbidden = ['marker', 'facecolor', 'edgecolor', 's']

    scatter_defaults = {
        's': 100,
        'linewidth': 2.0,
        'facecolor': 'none',
    }

    scatter_forbidden = ['linestyle', 'alpha', 'color']

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
            plot.set_ylim(_log_margin(*ylim))
        else:
            plot.set_yscale('linear')
            plot.set_ylim(_linear_margin(*ylim))
            plot.yaxis.get_major_formatter().set_scientific(True)
            plot.yaxis.get_major_formatter().set_powerlimits((-3, 4))
        plot.set_xlim(_linear_margin(*xlim))
        plot.locator_params(axis='x', nbins=7)

    def _plot(self):
        from soap.analysis.core import pareto_frontier
        try:
            return self.figure
        except AttributeError:
            pass
        from matplotlib import rc, pyplot
        rc('font', family='serif', size=24, serif='Times')
        rc('text', usetex=True)
        self.figure = pyplot.figure()
        plot = self.figure.add_subplot(111)
        colors = self._colors()
        color_groups = {}
        for d in self.result_list:
            if d['color_group'] is None:
                continue
            color_groups[d['color_group']] = next(colors)
        for r in self.result_list:
            d = r['kwargs']
            if not r['color_group'] is None:
                d['color'] = color_groups[r['color_group']]
            elif 'color' not in d:
                d['color'] = next(colors)
        markers = self._markers()
        xmin, xmax = ymin, ymax = float('Inf'), float('-Inf')
        for r in self.result_list:
            plot_kwargs = dict(self.plot_defaults)
            plot_kwargs.update(r['kwargs'])
            r['kwargs']['color'] = plot_kwargs['color']
            if r['frontier']:
                plot_kwargs['marker'] = None
                for k in self.plot_forbidden:
                    if k in plot_kwargs:
                        del plot_kwargs[k]
                result = sorted(pareto_frontier(r['result']))
                try:
                    area, error, expr = zip(*result)
                    logger.debug('legend', r['legend'])
                    lx, ly = _insert_region_frontier(area, error)
                except ValueError:
                    lx = ly = []
                plot.plot(lx, ly, **plot_kwargs)
                if lx and ly:
                    plot.fill_between(lx, ly, max(ly),
                                      alpha=0.1, color=plot_kwargs['color'])
                if r['annotate']:
                    for x, y, e in zip(area, error, expr):
                        plot.annotate(str(e), xy=(x, y), alpha=0.5)
        for r in self.result_list:
            scatter_kwargs = dict(self.scatter_defaults)
            scatter_kwargs.update(r['kwargs'])
            if 'marker' not in scatter_kwargs:
                scatter_kwargs['marker'] = next(markers)
            scatter_kwargs.setdefault('edgecolor', scatter_kwargs['color'])
            for k in self.scatter_forbidden:
                if k in scatter_kwargs:
                    del scatter_kwargs[k]
            if scatter_kwargs['marker'] == '.':
                scatter_kwargs['color'] = scatter_kwargs['edgecolor']
                del scatter_kwargs['edgecolor']
            if scatter_kwargs['marker'] == '+':
                scatter_kwargs['s'] *= 1.5
            try:
                area, error, _ = zip(*r['result'])
                xmin, xmax = min(xmin, min(area)), max(xmax, max(area))
                ymin, ymax = min(ymin, min(error)), max(ymax, max(error))
            except ValueError:
                area = error = []
            plot.scatter(area, error, label=r['legend'], **scatter_kwargs)
        self._auto_scale(plot, (xmin, xmax), (ymin, ymax))
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
        """Shows the plot"""
        from matplotlib import pyplot
        logger.info('Showing plot')
        self._plot()
        pyplot.show()

    def save(self, *args, **kwargs):
        """Saves the plot"""
        self._plot().savefig(*args, bbox_inches='tight', **kwargs)


def plot(result, **kwargs):
    """Oneliner for :class:`Plot`"""
    p = Plot(result, **kwargs)
    p.show()
    return p


def analyze_and_plot(s, v, d=None, f=None, o=False, t=True):
    from soap.transformer.utils import greedy_trace
    f = f or [greedy_trace]
    p = Plot(state=v, depth=d)
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
            if not o:
                continue
            legend += ' original'
            p.add_analysis(e, legend=legend, marker='o', color_group=i, s=400)
    except KeyboardInterrupt:
        pass
    return p


if __name__ == '__main__':
    logger.set_context(level=logger.levels.info)
    p = Plot(state={'x': [0, 1]})
    p.add_analysis('x * x + x + 1', legend='1')
    p.add_analysis('x * (x + 1) + 1', legend='2')
    p.add_analysis('1 + x + x * x', legend='3')
    p.show()
