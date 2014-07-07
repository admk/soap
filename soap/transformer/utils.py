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
from soap.analysis import expr_frontier


def closure(tree, **kwargs):
    """The full transitive closure."""
    return ArithTreeTransformer(tree, **kwargs).closure()


def full_closure(tree, **kwargs):
    """The same as :func:`closure`, ignoring the `kwargs` stuff."""
    return closure(tree)


def greedy_frontier_closure(tree, var_env, out_vars=None, prec=None, **kwargs):
    """Our greedy transitive closure.

    :param tree: The expression(s) under transform.
    :type tree:
        :class:`soap.expression.Expression` or
        :class:`soap.semantics.state.MetaState` or set, or str
    :param var_env: The ranges of input variables.
    :type var_env: dictionary containing mappings from variables to
        :class:`soap.semantics.error.Interval`
    :param out_vars: The output variables of the metastate
    :type out_vars: :class:`collections.Sequence`
    :param prec: Precision used to evaluate the expression, defaults to
        single precision.
    :type prec: int
    """
    plugin = lambda expr_set: expr_frontier(expr_set, var_env, out_vars, prec)
    transformer = ArithTreeTransformer(tree, step_plugin=plugin, **kwargs)
    return plugin(transformer.closure())


def transform(tree, reduction_rules=None, transform_rules=None,
              step_plugin=None, reduce_plugin=None, depth=None,
              multiprocessing=True):
    """One liner for :class:`soap.transformer.TreeTransformer`."""
    return TreeTransformer(
        tree, transform_rules=transform_rules, reduction_rules=reduction_rules,
        step_plugin=step_plugin, reduce_plugin=reduce_plugin,
        depth=depth, multiprocessing=multiprocessing).closure()


def expand(tree):
    """Fully expands the expression tree by distributivity.

    :param tree: The expression tree.
    :type tree: :class:`soap.expression.Expression` or str
    :returns: A fully expanded tree.
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
        tree, reduction_rules=reduction_rules, reduce_plugin=pop,
        multiprocessing=False).pop()


def reduce(tree):
    """Transforms tree by reduction rules only.

    :param tree: The expression tree.
    :type tree: :class:`soap.expression.Expression` or str
    :returns: A new expression tree.
    """
    if isinstance(tree, str) or is_expression(tree):
        t = transform(tree, ArithTreeTransformer.reduction_rules,
                      multiprocessing=False)
        s = set(t)
        if len(s) > 1:
            s.remove(tree)
        if len(s) == 1:
            return s.pop()
    with logger.local_context(level=logger.levels.info):
        if isinstance(tree, collections.Mapping):
            return MetaState({v: reduce(e) for v, e in tree.items()})
        if isinstance(tree, collections.Iterable):
            return {reduce(t) for t in tree}
    raise TypeError('Do not know how to reduce {!r}'.format(tree))


def parsings(tree):
    """Generates all possible parsings of the same tree by associativity.

    :param tree: The expression tree.
    :type tree: :class:`soap.expression.Expression` or str
    :returns: A set of trees.
    """
    return transform(
        tree, None, {
            operators.ADD_OP: [associativity_addition],
            operators.MULTIPLY_OP: [associativity_multiplication]
        })
