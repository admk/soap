import itertools

import matplotlib
from matplotlib import rc, pyplot
from mpl_toolkits.mplot3d import Axes3D

from soap import logger
from soap.analysis.core import pareto_frontier


_ZIGZAG_MARGIN = 1000.0
_SCATTER_MARGIN = 0.1


def _insert_region_frontier(points_2d, start_y=None, stop_x=None):
    new_points_2d = []
    py = start_y or points_2d[0][1] * _ZIGZAG_MARGIN
    for x, y in points_2d:
        new_points_2d.append((x, py))
        new_points_2d.append((x, y))
        py = y
    new_points_2d.append((stop_x or points_2d[-1][0] * _ZIGZAG_MARGIN, py))
    return new_points_2d


class PlotFinalizedError(Exception):
    """Plot is already finalized.  """


class Plot(object):
    def __init__(self, legend_pos=None):
        super().__init__()
        self.legend_pos = legend_pos
        figure = self.figure = pyplot.figure()
        self.ax3d = Axes3D(figure)
        self.colors = itertools.cycle('rgbkcmy')
        self.markers = itertools.cycle('+ox.sv^<>')
        self.legends = []
        self.projection_results = []
        self.is_finalized = False

    def values(self, result):
        return result.lut, result.error, result.latency, result.expression

    def add_original(self, original_point):
        self.add([original_point], 'Original')

    def add(self, optimized_results, legend=None):
        if self.is_finalized:
            raise PlotFinalizedError
        values = [self.values(r) for r in optimized_results]
        luts, errors, lats, exprs = zip(*values)
        color = next(self.colors)
        marker = next(self.markers)
        self.ax3d.scatter(
            luts, errors, lats, s=100, color=color, marker=marker)
        # add legend text to add later
        self.legends.append((color, marker, legend))
        # add results to plot projections later
        self.projection_results.append((color, values))

    def _add_projection_frontiers(self, xmin, xmax, ymin, ymax, zmin, zmax):
        def frontier(x, y, start, stop):
            points = pareto_frontier(zip(x, y), ignore_last=False)
            return zip(*_insert_region_frontier(sorted(points), start, stop))

        ax3d = self.ax3d
        for color, items in self.projection_results:
            if len(items) == 1:
                continue
            no_of_points = len(items)
            luts, errs, lats, exprs = zip(*items)
            luts_view = ([xmin] * no_of_points, errs, lats)
            errs_view = (luts, [ymax] * no_of_points, lats)
            lats_view = (luts, errs, [zmin] * no_of_points)
            ax3d.scatter(*luts_view, color=color, marker='.', alpha=0.5)
            ax3d.scatter(*errs_view, color=color, marker='.', alpha=0.5)
            ax3d.scatter(*lats_view, color=color, marker='.', alpha=0.5)
            f_errs, f_lats = frontier(errs, lats, zmax, ymax)
            ax3d.plot(
                [xmin] * len(f_errs), f_errs, f_lats,
                color=color, alpha=0.5)
            f_luts, f_lats = frontier(luts, lats, zmax, xmax)
            ax3d.plot(
                f_luts, [ymax] * len(f_lats), f_lats,
                color=color, alpha=0.5)
            f_luts, f_errs = frontier(luts, errs, ymax, xmax)
            ax3d.plot(
                f_luts, f_errs, [zmin] * len(f_luts),
                color=color, alpha=0.5)

    def _add_projection_lines(self, xmin, xmax, ymin, ymax, zmin, zmax):
        for color, items in self.projection_results:
            for lut, err, lat, expr in items:
                lines = [
                    ((lut, xmin), (err, err), (lat, lat)),
                    ((lut, lut), (err, ymax), (lat, lat)),
                    ((lut, lut), (err, err), (lat, zmin)),
                ]
                for arg in lines:
                    self.ax3d.plot(
                        *arg, linestyle='--', color=color, alpha=0.2)

    def _add_projections(self):
        """Add projections of points onto 2d planes.  """
        ax3d = self.ax3d
        xmin, xmax = ax3d.get_xlim()
        ymin, ymax = ax3d.get_ylim()
        zmin, zmax = ax3d.get_zlim()
        self._add_projection_frontiers(xmin, xmax, ymin, ymax, zmin, zmax)
        self._add_projection_lines(xmin, xmax, ymin, ymax, zmin, zmax)
        ax3d.set_xlim(xmin, xmax)
        ax3d.set_ylim(ymin, ymax)
        ax3d.set_zlim(zmin, zmax)

    def _set_labels(self):
        """Set names for axes.  """
        ax3d = self.ax3d
        ax3d.set_xlabel('Resources (LUTs)')
        ax3d.xaxis.get_major_formatter().set_scientific(True)
        ax3d.xaxis.get_major_formatter().set_powerlimits((-3, 3))
        ax3d.set_ylabel('Error')
        ax3d.yaxis.get_major_formatter().set_scientific(True)
        ax3d.yaxis.get_major_formatter().set_powerlimits((-3, 4))
        ax3d.set_zlabel('Latency')

    def _add_legend(self):
        legends = []
        proxies = []
        for color, marker, legend in self.legends:
            proxy = matplotlib.lines.Line2D(
                [0], [0], linestyle="none", color=color, marker=marker)
            proxies.append(proxy)
            legends.append(legend)
        self.ax3d.legend(proxies, legends, numpoints=1)

    def finalize(self):
        if self.is_finalized:
            return
        self.is_finalized = True
        self._add_projections()
        self._set_labels()
        self._add_legend()

    def save(self, name):
        self.finalize()
        self.figure.savefig(name, bbox_inches='tight')

    def show(self):
        self.finalize()
        pyplot.show()


def plot(result, **kwargs):
    """Oneliner for :class:`Plot`"""
    p = Plot(result, **kwargs)
    p.show()
    return p


rc('font', family='Times New Roman', size=15)
rc('figure', autolayout=True)
# rc('figure.subplot', bottom=0.5)
