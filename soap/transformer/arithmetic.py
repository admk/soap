"""
.. module:: soap.transformer.arithmetic
    :synopsis: Transforms arithmetic expression instances.
"""
from soap.expression.common import ADD_OP, MULTIPLY_OP, is_constant
from soap.transformer.core import TreeTransformer
from soap.transformer.pattern import (
    pattern_transformer_group, pattern_transformer_factory
)


_associativity = pattern_transformer_group(
    (['(a + b) + c', 'c + (a + b)'], ['(a + c) + b', '(b + c) + a'],
     'associativity_addition'),
    (['(a * b) * c', 'c * (a * b)'], ['(a * c) * b', '(b * c) * a'],
     'associativity_multiplication'),
    name='associativity')
_distribute_for_distributivity = pattern_transformer_factory(
    ['(a + b) * c', 'c * (a + b)'], ['a * c + b * c'],
    'distribute_for_distributivity')
_collect_for_distributivity = pattern_transformer_factory(
    ['a * c + b * c', 'a * c + c * b', 'c * a + c * b', 'c * a + b * c'],
    ['(a + b) * c'], 'collect_for_distributivity')

multiplicative_identity_reduction = pattern_transformer_factory(
    ['a * 1', '1 * a'], ['a'], 'multiplicative_identity_reduction')
additive_identity_reduction = pattern_transformer_factory(
    ['a + 0', '0 + a'], ['a'], 'additive_identity_reduction')
zero_reduction = pattern_transformer_factory(
    ['a * 0', '0 * a'], ['0'], 'zero_reduction')


def associativity(expression):
    return _associativity(expression)


def distribute_for_distributivity(expression):
    return _distribute_for_distributivity(expression)


def collect_for_distributivity(expression):
    return _collect_for_distributivity(expression)


def constant_reduction(t):
    """Constant propagation.

    For example:
        1 + 2 == 3

    :param t: The expression tree.
    :type t: :class:`soap.expression.BinaryArithExpr`
    :returns: A list containing an expression related by this reduction rule.
    """
    if not all(is_constant(a) for a in t.args):
        return set()
    if t.op == MULTIPLY_OP:
        return {t.a1 * t.a2}
    if t.op == ADD_OP:
        return {t.a1 + t.a2}


class ArithTreeTransformer(TreeTransformer):
    """The class that provides transformation of binary operator expressions.

    It has the same arguments as :class:`soap.transformer.TreeTransformer`,
    which is the class it is derived from.
    """
    transform_methods = [
        associativity,
        distribute_for_distributivity,
        collect_for_distributivity,
    ]
    reduction_methods = [
        multiplicative_identity_reduction,
        additive_identity_reduction,
        zero_reduction,
        constant_reduction,
    ]
