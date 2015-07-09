"""
.. module:: soap.transformer.arithmetic
    :synopsis: Transforms arithmetic expression instances.
"""
from patmat.mimic import Pred, Val

from soap.expression import expression_factory, operators, SelectExpr
from soap.semantics.functions import arith_eval
from soap.semantics.state import BoxState
from soap.transformer.core import TreeTransformer
from soap.transformer.pattern import compile, ExprConstPropMimic, ExprMimic


associativity_addition = (
    compile('(a + b) + c'),
    compile('(a + c) + b', '(b + c) + a'),
    'associativity_addition'
)
associativity_multiplication = (
    compile('(a * b) * c'),
    compile('(a * c) * b', '(b * c) * a'),
    'associativity_multiplication'
)
associativity_division = (
    compile('(a / b) / c', 'a / (b * c)'),
    compile('(a / b) / c', 'a / (b * c)', '(a / c) / b'),
    'associativity_division'
)

negation_1 = (
    compile('a - b'),
    compile('a + -b'),
    'negation_1'
)
negation_2 = (
    compile('a - -b'),
    compile('a + b'),
    'negation_2'
)
unnegation_1 = (
    compile('a + -b'),
    compile('a - b'),
    'unnegation_1'
)
unnegation_2 = (
    compile('a + b'),
    compile('a - -b'),
    'unnegation_2'
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
    compile('-(a + b)'),
    compile('-a - b', '-b - a'),
    'distributivity_distribute_unary_subtraction_addition'
)
distributivity_distribute_unary_subtraction_subtraction = (
    compile('-(a - b)'),
    compile('-a + b', 'b - a'),
    'distributivity_distribute_unary_subtraction_addition'
)
distributivity_distribute_unary_subtraction_multiplication = (
    compile('-(a * b)'),
    compile('-a * b', 'a * -b'),
    'distributivity_distribute_unary_subtraction_multiplication'
)
distributivity_distribute_unary_subtraction_division = (
    compile('-(a / b)'),
    compile('-a / b', 'a / -b'),
    'distributivity_distribute_unary_subtraction_division'
)
distributivity_distribute_unary_subtraction_select = (
    compile('-(b ? c : d)'),
    compile('b ? -c : -d'),
    'distributivity_distribute_unary_subtraction_select'
)

distributivity_distribute_multiplication = (
    compile('(a + b) * c'),
    compile('a * c + b * c'),
    'distributivity_distribute_multiplication'
)
distributivity_distribute_division = (
    compile('(a + b) / c'),
    compile('a / c + b / c'),
    'distributivity_distribute_division'
)
distributivity_distribute_select = (
    compile(ExprMimic(
        op=Val('op'),
        args=[
            ExprMimic(op=operators.TERNARY_SELECT_OP, args=Val('args')),
            Val('da')])),
    compile(distributivity_distribute_select_func),
    'distributivity_distribute_select'
)

distributivity_collect_multiplication = (
    compile('a * c + b * c'),
    compile('(a + b) * c'),
    'distributivity_collect_multiplication'
)
distributivity_collect_multiplication_1 = (
    compile('a + a * b'),
    compile('a * (1 + b)'),
    'distributivity_collect_multiplication_1'
)
distributivity_collect_multiplication_2 = (
    compile('a + a'),
    compile('2 * a'),
    'distributivity_collect_multiplication_2'
)
distributivity_collect_division = (
    compile('a / c + b'),
    compile('(a + b * c) / c'),
    'distributivity_collect_division'
)
distributivity_collect_division_1 = (
    compile('a / c + b / c'),
    compile('(a + b) / c'),
    'distributivity_collect_division_1'
)
distributivity_collect_division_2 = (
    compile('a / c + b / d'),
    compile('(a * d + b * c) / (c * d)'),
    'distributivity_collect_division_2'
)
distributivity_collect_select_addition = (
    compile('b ? (a + d) : (c + d)'),
    compile('(b ? a : c) + d'),
    'distributivity_collect_select_addition'
)
distributivity_collect_select_subtraction_1 = (
    compile('b ? (a - d) : (c - d)'),
    compile('(b ? a : c) - d'),
    'distributivity_collect_select_subtraction_1'
)
distributivity_collect_select_subtraction_2 = (
    compile('b ? (d - a) : (d - c)'),
    compile('d - (b ? a : c)'),
    'distributivity_collect_select_subtraction_2'
)
distributivity_collect_select_multiplication = (
    compile('b ? (a * d) : (c * d)'),
    compile('(b ? a : c) * d'),
    'distributivity_collect_select_multiplication'
)
distributivity_collect_select_division_1 = (
    compile('b ? (a / d) : (c / d)'),
    compile('(b ? a : c) / d'),
    'distributivity_collect_select_division_1'
)
distributivity_collect_select_division_2 = (
    compile('b ? (d / a) : (d / c)'),
    compile('d / (b ? a : c)'),
    'distributivity_collect_select_division_2'
)

inversive_division = (
    compile('a / (b / c)'),
    compile('(a * c) / b'),
    'inversive_division'
)

# FIXME separate rules for complimentaries
commutativity_select_1 = (
    compile('d ? (b ? a : c) : e',
            'b ? (d ? a : e) : (d ? c : e)'),
    compile('d ? (b ? a : c) : e',
            'b ? (d ? a : e) : (d ? c : e)'),
    'commutativity_select_1'
)
commutativity_select_2 = (
    compile('b ? a : (d ? c : e)',
            'd ? (b ? a : c) : (b ? a : e)'),
    compile('b ? a : (d ? c : e)',
            'd ? (b ? a : c) : (b ? a : e)'),
    'commutativity_select_2'
)

identity_reduction_addition = (
    compile('a + 0'),
    compile('a'),
    'additive_identity_reduction'
)
identity_reduction_multiplication = (
    compile('a * 1'),
    compile('a'),
    'identity_reduction_multiplication'
)
identity_reduction_division = (
    compile('a / 1'),
    compile('a'),
    'identity_reduction_division'
)

double_negation_reduction = (
    compile('--a'),
    compile('a'),
    'double_negation_reduction'
)

zero_reduction_subtraction = (
    compile('a - a'),
    compile('0'),
    'zero_reduction_subtraction'
)
zero_reduction_multiplication = (
    compile('a * 0'),
    compile('0'),
    'zero_reduction_multiplication'
)
zero_reduction_division = (
    compile('0 / a'),
    compile('0'),
    'zero_reduction_division'
)

one_reduction_division = (
    compile('a / a'),
    compile('1'),
    'one_reduction_division'
)


def _constant_reduction_func(op, args):
    return arith_eval(expression_factory(op, *args), BoxState(bottom=True))

constant_reduction = (
    compile(ExprConstPropMimic()),
    compile(_constant_reduction_func),
    'constant_reduction'
)

same_expression_reduction_ifelse = (
    compile('b ? a : a'),
    compile('a'),
    'same_expression_reduction_ifelse'
)


def boolean_mirror_func(op, a1, a2):
    op = operators.COMPARISON_MIRROR_DICT[op]
    return expression_factory(op, a2, a1)


boolean_mirror = (
    compile(ExprMimic(op=Val('op'), args=[Val('a1'), Val('a2')])),
    compile(boolean_mirror_func),
    'boolean_mirror'
)


_boolean_rearrange_dict = {
    operators.ADD_OP: operators.SUBTRACT_OP,
    operators.SUBTRACT_OP: operators.ADD_OP,
}


def boolean_rearrange_pred(op):
    return op in _boolean_rearrange_dict


def boolean_rearrange_func(op, a1, opr, a2, a3):
    lhs = expression_factory(_boolean_rearrange_dict[opr], a1, a3)
    return expression_factory(op, lhs, a2)


boolean_rearrange = (
    compile(ExprMimic(
        op=Val('op'), args=[
            Val('a1'), ExprMimic(
                op=Pred(boolean_rearrange_pred, Val('opr')),
                args=[Val('a2'), Val('a3')])])),
    compile(boolean_rearrange_func),
    'boolean_rearrange'
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
            unnegation_1,
            unnegation_2,
        ],
        operators.SUBTRACT_OP: [
            distributivity_distribute_select,
            negation_1,
            negation_2,
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
            commutativity_select_1,
            commutativity_select_2,
        ],
    }
    boolean_rules = {
        operators.EQUAL_OP: [
            boolean_mirror,
            boolean_rearrange
        ],
        operators.NOT_EQUAL_OP: [
            boolean_mirror,
            boolean_rearrange
        ],
        operators.GREATER_OP: [
            boolean_mirror,
            boolean_rearrange
        ],
        operators.GREATER_EQUAL_OP: [
            boolean_mirror,
            boolean_rearrange
        ],
        operators.LESS_OP: [
            boolean_mirror,
            boolean_rearrange
        ],
        operators.LESS_EQUAL_OP: [
            boolean_mirror,
            boolean_rearrange
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
            constant_reduction,
        ],
        operators.TERNARY_SELECT_OP: [
            same_expression_reduction_ifelse,
        ],
    }
