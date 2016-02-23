"""
.. module:: soap.transformer.utils
    :synopsis: Useful utility functions to simplify calls to
        ArithTreeTransformer.
"""
import collections

from soap import logger
from soap.expression import operators, is_expression
from soap.semantics import MetaState
from soap.transformer.core import TreeTransformer
from soap.transformer.arithmetic import (
    associativity_addition, associativity_multiplication,
    distributivity_distribute_multiplication,
    distributivity_distribute_division, ArithTreeTransformer
)
from soap.analysis import frontier, thick_frontier


def closure(expr, **kwargs):
    """The full transitive closure."""
    return ArithTreeTransformer(expr, **kwargs).closure()


def full_closure(expr, **kwargs):
    """The same as :func:`closure`, ignoring the `kwargs` stuff."""
    return closure(expr)


def _plugin_closure(
        plugin_func, expr, state, out_vars, recurrences=None, **kwargs):
    def plugin(expr_set):
        frontier_set = plugin_func(
            expr_set, state, out_vars, recurrences=recurrences)
        return [r.expression for r in frontier_set]
    transformer = ArithTreeTransformer(expr, step_plugin=plugin, **kwargs)
    return plugin(transformer.closure())


def greedy_frontier_closure(
        expr, state, out_vars=None, recurrences=None, **kwargs):
    """Our greedy transitive closure.

    :param expr: The expression(s) under transform.
    :type expr:
        :class:`soap.expression.Expression` or
        :class:`soap.semantics.state.MetaState`
    :param state: The ranges of input variables.
    :type state: dictionary containing mappings from variables to
        :class:`soap.semantics.error.Interval`
    :param out_vars: The output variables of the metastate
    :type out_vars: :class:`collections.Sequence`
    :param recurrences: A dictionary containing information about
        loop recurrences
    :type recurrences: dict
    """
    return _plugin_closure(
        frontier, expr, state, out_vars, recurrences, **kwargs)


def thick_frontier_closure(
        expr, state, out_vars=None, recurrences=None, **kwargs):
    """Our thick frontier transitive closure.

    :param expr: The expression(s) under transform.
    :type expr:
        :class:`soap.expression.Expression` or
        :class:`soap.semantics.state.MetaState`
    :param state: The ranges of input variables.
    :type state: dictionary containing mappings from variables to
        :class:`soap.semantics.error.Interval`
    :param out_vars: The output variables of the metastate
    :type out_vars: :class:`collections.Sequence`
    :param recurrences: A dictionary containing information about
        loop recurrences
    :type recurrences: dict
    """
    return _plugin_closure(
        thick_frontier, expr, state, out_vars, recurrences, **kwargs)


def transform(expr, reduction_rules=None, transform_rules=None,
              step_plugin=None, reduce_plugin=None, depth=None,
              multiprocessing=True):
    """One liner for :class:`soap.transformer.TreeTransformer`."""
    return TreeTransformer(
        expr, transform_rules=transform_rules, reduction_rules=reduction_rules,
        step_plugin=step_plugin, reduce_plugin=reduce_plugin,
        depth=depth, multiprocessing=multiprocessing).closure()


def expand(expr, *args, **kwargs):
    """Fully expands the expression expr by distributivity.

    :param expr: The expression expr.
    :type expr: :class:`soap.expression.Expression` or str
    :returns: A fully expanded expr.
    """
    def pop(s):
        if s:
            return [s.pop()]
        return s
    reduction_rules = [
        distributivity_distribute_multiplication,
        distributivity_distribute_division,
    ]
    return transform(
        expr, reduction_rules=reduction_rules, reduce_plugin=pop,
        multiprocessing=False).pop()


def reduce(expr, *args, **kwargs):
    """Transforms expr by reduction rules only.

    :param expr: The expression expr.
    :type expr: :class:`soap.expression.Expression` or str
    :returns: A new expression expr.
    """
    if isinstance(expr, str) or is_expression(expr):
        t = transform(expr, ArithTreeTransformer.reduction_rules,
                      multiprocessing=False)
        s = set(t)
        if len(s) > 1:
            s.remove(expr)
        if len(s) == 1:
            return s.pop()
    with logger.local_context(level=logger.levels.info):
        if isinstance(expr, collections.Mapping):
            return MetaState({v: reduce(e) for v, e in expr.items()})
        if isinstance(expr, collections.Iterable):
            return {reduce(t) for t in expr}
    raise TypeError('Do not know how to reduce {!r}'.format(expr))


def parsings(expr, *args, **kwargs):
    """Generates all possible parsings of the same expr by associativity.

    :param expr: The expression expr.
    :type expr: :class:`soap.expression.Expression` or str
    :returns: A set of exprs.
    """
    return transform(
        expr, None, {
            operators.ADD_OP: [associativity_addition],
            operators.MULTIPLY_OP: [associativity_multiplication]
        }, depth=1000)
