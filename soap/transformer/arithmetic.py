"""
.. module:: soap.transformer.arithmetic
    :synopsis: Transforms arithmetic expression instances.
"""
from patmat.mimic import Val

from soap.expression import expression_factory, operators, SelectExpr
from soap.transformer import pattern
from soap.transformer.core import TreeTransformer
from soap.semantics.functions import arith_eval
from soap.semantics.state import BoxState


associativity_addition = (
    pattern.compile('(a + b) + c'),
    pattern.compile('(a + c) + b', '(b + c) + a'),
    'associativity_addition'
)
associativity_multiplication = (
    pattern.compile('(a * b) * c'),
    pattern.compile('(a * c) * b', '(b * c) * a'),
    'associativity_multiplication'
)
associativity_division = (
    pattern.compile('(a / b) / c', 'a / (b * c)'),
    pattern.compile('(a / b) / c', 'a / (b * c)', '(a / c) / b'),
    'associativity_division'
)

negation = (
    pattern.compile('a - b'),
    pattern.compile('a + -b'),
    'negation'
)


def distributivity_distribute_subtraction_func(op, args):
    args = [expression_factory(operators.UNARY_SUBTRACT_OP, a) for a in args]
    return expression_factory(op, *args)


def distributivity_distribute_select_func(op, args, da):
    bool_expr, true_expr, false_expr = args
    return SelectExpr(
        bool_expr,
        expression_factory(op, true_expr, da),
        expression_factory(op, false_expr, da))


distributivity_distribute_unary_subtraction_addition = (
    pattern.compile('-(a + b)'),
    pattern.compile('-a - b'),
    'distributivity_distribute_unary_subtraction_addition'
)
distributivity_distribute_unary_subtraction_subtraction = (
    pattern.compile('-(a - b)'),
    pattern.compile('-a + b'),
    'distributivity_distribute_unary_subtraction_addition'
)
distributivity_distribute_unary_subtraction_multiplication = (
    pattern.compile('-(a * b)'),
    pattern.compile('-a * b', 'a * -b'),
    'distributivity_distribute_unary_subtraction_multiplication'
)
distributivity_distribute_unary_subtraction_division = (
    pattern.compile('-(a / b)'),
    pattern.compile('-a / b', 'a / -b'),
    'distributivity_distribute_unary_subtraction_division'
)
distributivity_distribute_unary_subtraction_select = (
    pattern.compile('-(b if c else d)'),
    pattern.compile('-b if c else -d'),
    'distributivity_distribute_unary_subtraction_select'
)

distributivity_distribute_multiplication = (
    pattern.compile('(a + b) * c'),
    pattern.compile('a * c + b * c'),
    'distributivity_distribute_multiplication'
)
distributivity_distribute_division = (
    pattern.compile('(a + b) / c'),
    pattern.compile('a / c + b / c'),
    'distributivity_distribute_division'
)
distributivity_distribute_select = (
    pattern.compile(pattern.ExprMimic(
        op=Val('op'), args=[
            pattern.ExprMimic(
                op=operators.TERNARY_SELECT_OP, args=Val('args')),
            Val('da')])),
    pattern.compile(distributivity_distribute_select_func),
    'distributivity_distribute_select'
)

distributivity_collect_multiplication = (
    pattern.compile('a * c + b * c'),
    pattern.compile('(a + b) * c'),
    'distributivity_collect_multiplication'
)
distributivity_collect_multiplication_1 = (
    pattern.compile('a + a * b'),
    pattern.compile('a * (1 + b)'),
    'distributivity_collect_multiplication_1'
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
distributivity_collect_select_addition = (
    pattern.compile('(a + d) if b else (c + d)'),
    pattern.compile('(a if b else c) + d'),
    'distributivity_collect_select_addition'
)
distributivity_collect_select_subtraction_1 = (
    pattern.compile('(a - d) if b else (c - d)'),
    pattern.compile('(a if b else c) - d'),
    'distributivity_collect_select_subtraction_1'
)
distributivity_collect_select_subtraction_2 = (
    pattern.compile('(d - a) if b else (d - c)'),
    pattern.compile('d - (a if b else c)'),
    'distributivity_collect_select_subtraction_2'
)
distributivity_collect_select_multiplication = (
    pattern.compile('(a * d) if b else (c * d)'),
    pattern.compile('(a if b else c) * d'),
    'distributivity_collect_select_multiplication'
)
distributivity_collect_select_division_1 = (
    pattern.compile('(a / d) if b else (c / d)'),
    pattern.compile('(a if b else c) / d'),
    'distributivity_collect_select_division_1'
)
distributivity_collect_select_division_2 = (
    pattern.compile('(d / a) if b else (d / c)'),
    pattern.compile('d / (a if b else c)'),
    'distributivity_collect_select_division_2'
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

double_negation_reduction = (
    pattern.compile('--a'),
    pattern.compile('a'),
    'double_negation_reduction'
)

zero_reduction_subtraction = (
    pattern.compile('a - a'),
    pattern.compile('0'),
    'zero_reduction_subtraction'
)
zero_reduction_multiplication = (
    pattern.compile('a * 0'),
    pattern.compile('0'),
    'zero_reduction_multiplication'
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
    return arith_eval(expression_factory(op, *args), BoxState(bottom=True))

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
            distributivity_distribute_select,
        ],
        operators.SUBTRACT_OP: [
            negation,
            distributivity_distribute_select,
        ],
        operators.MULTIPLY_OP: [
            associativity_multiplication,
            distributivity_distribute_multiplication,
            distributivity_distribute_select,
        ],
        operators.DIVIDE_OP: [
            associativity_division,
            distributivity_distribute_division,
            distributivity_distribute_select,
            inversive_division,
        ],
        operators.UNARY_SUBTRACT_OP: [
            distributivity_distribute_unary_subtraction_addition,
            distributivity_distribute_unary_subtraction_subtraction,
            distributivity_distribute_unary_subtraction_multiplication,
            distributivity_distribute_unary_subtraction_division,
            distributivity_distribute_unary_subtraction_select,
        ],
        operators.TERNARY_SELECT_OP: [
            distributivity_collect_select_addition,
            distributivity_collect_select_subtraction_1,
            distributivity_collect_select_subtraction_2,
            distributivity_collect_select_multiplication,
            distributivity_collect_select_division_1,
            distributivity_collect_select_division_2,
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
        operators.UNARY_SUBTRACT_OP: [
            double_negation_reduction,
            zero_reduction_subtraction,
        ],
    }


class MartelTreeTransformer(ArithTreeTransformer):
    """
    Some compatibility hacks to support martel's equivalence finding, so we can
    compare.
    """

    reduction_methods = []

    def _harvest(self, trees):
        return trees

    def _seed(self, trees):
        return trees

    def _step(self, expressions, closure=False, depth=None):
        return super()._step(expressions, closure, self.depth)
