"""
.. module:: soap.transformer.arithmetic
    :synopsis: Transforms arithmetic expression instances.
"""
import patmat

from soap.expression.common import op_func_dict_by_ary_list
from soap.transformer import pattern
from soap.transformer.core import TreeTransformer


def _constant_2_ary_reduction_func(op, a, b):
    return op_func_dict_by_ary_list[1][op](a, b)


associativity_addition = (
    pattern.compile('(a + b) + c', 'c + (a + b)'),
    pattern.compile('(a + c) + b', '(b + c) + a'),
    'associativity_addition'
)
associativity_multiplication = (
    pattern.compile('(a * b) * c', 'c * (a * b)'),
    pattern.compile('(a * c) * b', '(b * c) * a'),
    'associativity_multiplication'
)

distribute_for_distributivity = (
    pattern.compile('(a + b) * c', 'c * (a + b)'),
    pattern.compile('a * c + b * c'),
    'distribute_for_distributivity'
)
collect_for_distributivity = (
    pattern.compile(
        'a * c + b * c', 'a * c + c * b', 'c * a + c * b', 'c * a + b * c'),
    pattern.compile('(a + b) * c'),
    'collect_for_distributivity'
)

multiplicative_identity_reduction = (
    pattern.compile('a * 1', '1 * a'),
    pattern.compile('a'),
    'multiplicative_identity_reduction'
)
additive_identity_reduction = (
    pattern.compile('a + 0', '0 + a'),
    pattern.compile('a'),
    'additive_identity_reduction'
)
zero_reduction = (
    pattern.compile('a * 0', '0 * a'),
    pattern.compile('0'),
    'zero_reduction'
)

constant_2_ary_reduction = (
    pattern.compile(
        pattern.ExprMimic(
            op=patmat.Val('op'),
            args=[
                pattern.ConstVal('a'),
                pattern.ConstVal('b'),
            ])),
    pattern.compile(_constant_2_ary_reduction_func),
    'constant_2_ary_reduction'
)


class ArithTreeTransformer(TreeTransformer):
    """The class that provides transformation of binary operator expressions.

    It has the same arguments as :class:`soap.transformer.TreeTransformer`,
    which is the class it is derived from.
    """
    transform_rules = [
        associativity_addition,
        associativity_multiplication,
        distribute_for_distributivity,
        collect_for_distributivity,
    ]
    reduction_rules = [
        multiplicative_identity_reduction,
        additive_identity_reduction,
        zero_reduction,
        constant_2_ary_reduction,
    ]
