"""
.. module:: soap.transformer.utils
    :synopsis: Useful utility functions to simplify calls to
        ArithTreeTransformer.
"""
from soap import logger
from soap.expression import operators
from soap.expression.common import is_expr
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


def greedy_frontier_closure(tree, var_env=None, prec=None, **kwargs):
    """Our greedy transitive closure.

    :param tree: The expression(s) under transform.
    :type tree: :class:`soap.expression.Expression`, set, or str
    :param var_env: The ranges of input variables.
    :type var_env: dictionary containing mappings from variables to
        :class:`soap.semantics.error.Interval`
    :param prec: Precision used to evaluate the expression, defaults to
        single precision.
    :type prec: int
    """
    if var_env:
        func = lambda s: expr_frontier(s, var_env, prec)
    else:
        func = None
    closure = ArithTreeTransformer(tree, step_plugin=func, **kwargs).closure()
    return expr_frontier(closure, var_env, prec)


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
    if not is_expr(tree):
        with logger.local_context(level=logger.levels.info):
            return {reduce(t) for t in tree}
    t = transform(tree, ArithTreeTransformer.reduction_rules,
                  multiprocessing=False)
    s = set(t)
    if len(s) > 1:
        s.remove(tree)
    if len(s) == 1:
        return s.pop()
    raise Exception


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


def martel_trace(tree, var_env=None, depth=2, prec=None, **kwargs):
    """Finds Martel's equivalent expressions.

    :param tree: The original expression.
    :type tree: :class:`soap.expression.Expression` or str
    :param var_env: The ranges of input variables.
    :type var_env: dictionary containing mappings from variables to
        :class:`soap.semantics.error.Interval`
    :param depth: The depth limit.
    :type depth: int
    :param prec: Precision used to evaluate the expression, defaults to
        single precision.
    :type prec: int
    """
    from soap.transformer.trace import MartelTraceExpr
    expression = MartelTraceExpr(tree.op, *tree.args)
    return reduce(expression.traces(var_env, depth, prec, **kwargs))


def greedy_trace(tree, var_env=None, depth=2, prec=None, **kwargs):
    """Finds our equivalent expressions using :class:`GreedyTraceExpr`.

    :param tree: The original expression.
    :type tree: :class:`soap.expression.Expression` or str
    :param var_env: The ranges of input variables.
    :type var_env: dictionary containing mappings from variables to
        :class:`soap.semantics.error.Interval`
    :param depth: The depth limit.
    :type depth: int
    :param prec: Precision used to evaluate the expression, defaults to
        single precision.
    :type prec: int
    """
    from soap.transformer.trace import GreedyTraceExpr
    expression = GreedyTraceExpr(*tree)
    return reduce(expression.traces(var_env, depth, prec, **kwargs))


def frontier_trace(tree, var_env=None, depth=2, prec=None, **kwargs):
    """Finds our equivalent expressions using :class:`FrontierTraceExpr`.

    :param tree: The original expression.
    :type tree: :class:`soap.expression.Expression` or str
    :param var_env: The ranges of input variables.
    :type var_env: dictionary containing mappings from variables to
        :class:`soap.semantics.error.Interval`
    :param depth: The depth limit.
    :type depth: int
    :param prec: Precision used to evaluate the expression, defaults to
        single precision.
    :type prec: int
    """
    from soap.transformer.trace import FrontierTraceExpr
    expression = FrontierTraceExpr(*tree)
    return reduce(expression.traces(var_env, depth, prec, **kwargs))
