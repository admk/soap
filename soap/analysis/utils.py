"""
.. module:: soap.analysis.utils
    :synopsis: Provides utility functions for analysis and plotting.
"""
from soap.analysis.core import Analysis


def analyze(expr_set, state, out_vars=None, **kwargs):
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
    return Analysis(expr_set, state, out_vars, **kwargs).analyze()


def frontier(expr_set, state, out_vars=None, **kwargs):
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
    return Analysis(expr_set, state, out_vars, **kwargs).frontier()


def thick_frontier(expr_set, state, out_vars=None, **kwargs):
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
    return Analysis(expr_set, state, out_vars, **kwargs).thick_frontier()
