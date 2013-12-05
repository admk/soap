"""
.. module:: soap.transformer.arithmetic
    :synopsis: Transforms arithmetic expression instances.
"""
from soap.expression import operators
from soap.transformer import pattern
from soap.transformer.core import TreeTransformer


associativity_addition = (
    pattern.compile('(a + b) + c'),
    pattern.compile('(a + c) + b', '(b + c) + a'),
    'associativity_addition',
)
associativity_multiplication = (
    pattern.compile('(a * b) * c'),
    pattern.compile('(a * c) * b', '(b * c) * a'),
    'associativity_multiplication',
)
associativity_division = (
    pattern.compile('(a / b) / c', 'a / (b * c)'),
    pattern.compile('(a / b) / c', 'a / (b * c)', '(a / c) / b'),
    'associativity_division',
)

distributivity_distribute_multiplication = (
    pattern.compile('(a + b) * c'),
    pattern.compile('a * c + b * c'),
    'distributivity_distribute_multiplication',
)
distributivity_distribute_division = (
    pattern.compile('(a + b) / c'),
    pattern.compile('a / c + b / c'),
    'distributivity_distribute_division',
)

distributivity_collect_multiplication = (
    pattern.compile('a * c + b * c'),
    pattern.compile('(a + b) * c'),
    'distributivity_collect_multiplication',
)
distributivity_collect_multiplication_1 = (
    pattern.compile('a + a * b'),
    pattern.compile('a * (1 + b)'),
    'distributivity_collect_multiplication_1',
)
distributivity_collect_multiplication_2 = (
    pattern.compile('a + a'),
    pattern.compile('2 * a'),
    'distributivity_collect_multiplication_2'
)
distributivity_collect_division = (
    pattern.compile('a / c + b'),
    pattern.compile('(a + b * c) / c'),
    'distributivity_collect_division'
)
distributivity_collect_division_1 = (
    pattern.compile('a / c + b / c'),
    pattern.compile('(a + b) / c'),
    'distributivity_collect_division_1'
)
distributivity_collect_division_2 = (
    pattern.compile('a / c + b / d'),
    pattern.compile('(a * d + b * c) / (c * d)'),
    'distributivity_collect_division_2'
)

inversive_division = (
    pattern.compile('a / (b / c)'),
    pattern.compile('(a * c) / b'),
    'inversive_division'
)

identity_reduction_addition = (
    pattern.compile('a + 0'),
    pattern.compile('a'),
    'additive_identity_reduction'
)
identity_reduction_multiplication = (
    pattern.compile('a * 1'),
    pattern.compile('a'),
    'identity_reduction_multiplication'
)
identity_reduction_division = (
    pattern.compile('a / 1'),
    pattern.compile('a'),
    'identity_reduction_division'
)

zero_reduction_multiplication = (
    pattern.compile('a * 0'),
    pattern.compile('0'),
    'zero_reduction'
)
zero_reduction_division = (
    pattern.compile('0 / a'),
    pattern.compile('0'),
    'zero_reduction_division'
)

one_reduction_division = (
    pattern.compile('a / a'),
    pattern.compile('1'),
    'one_reduction_division'
)


def _constant_reduction_func(op, args):
    return operators.op_func_dict_by_ary_list[len(args) - 1][op](*args)

constant_reduction = (
    pattern.compile(pattern.ExprConstPropMimic()),
    pattern.compile(_constant_reduction_func),
    'constant_reduction'
)


class ArithTreeTransformer(TreeTransformer):
    """The class that provides transformation of binary operator expressions.

    It has the same arguments as :class:`soap.transformer.TreeTransformer`,
    which is the class it is derived from.
    """
    transform_rules = {
        operators.ADD_OP: [
            associativity_addition,
            distributivity_collect_multiplication,
            distributivity_collect_multiplication_1,
            distributivity_collect_multiplication_2,
            distributivity_collect_division,
            distributivity_collect_division_1,
            distributivity_collect_division_2,
        ],
        operators.SUBTRACT_OP: [],
        operators.MULTIPLY_OP: [
            associativity_multiplication,
            distributivity_distribute_multiplication,
        ],
        operators.DIVIDE_OP: [
            associativity_division,
            distributivity_distribute_division,
            inversive_division,
        ],
    }
    reduction_rules = {
        operators.ADD_OP: [
            identity_reduction_addition,
            constant_reduction,
        ],
        operators.SUBTRACT_OP: [
            constant_reduction,
        ],
        operators.MULTIPLY_OP: [
            identity_reduction_multiplication,
            zero_reduction_multiplication,
            constant_reduction,
        ],
        operators.DIVIDE_OP: [
            identity_reduction_division,
            zero_reduction_division,
            one_reduction_division,
            constant_reduction,
        ],
    }
