"""
.. module:: soap.expression.common
    :synopsis: Common definitions for expressions.
"""
from soap.common.cache import cached


def is_variable(e):
    from soap.expression.variable import Variable
    return isinstance(e, Variable)


def is_expression(e):
    from soap.expression.base import Expression
    from soap.expression.variable import Variable
    return isinstance(e, Expression) and not isinstance(e, Variable)


def is_arith_expr(e):
    """Check if `e` is an expression."""
    from soap.expression.arithmetic import ArithExpr
    return isinstance(e, ArithExpr)


def is_bool_expr(e):
    """Check if `e` is a boolean expression."""
    from soap.expression.boolean import BoolExpr
    return isinstance(e, BoolExpr)


def concat_multi_expr(*expr_args):
    """Concatenates multiple expressions into a single expression by using the
    barrier operator.
    """
    me = None
    for e in expr_args:
        me = me | e if me else e
    return me


def split_multi_expr(e):
    """Splits the single expression into multiple expressions."""
    from soap.expression.operators import BARRIER_OP
    if e.op != BARRIER_OP:
        return [e]
    return split_multi_expr(e.a1) + split_multi_expr(e.a2)


@cached
def expression_factory(op, *args):
    from soap.expression import operators
    from soap.expression.variable import Variable
    from soap.expression.arithmetic import (
        UnaryArithExpr, BinaryArithExpr, TernaryArithExpr, SelectExpr
    )
    from soap.expression.boolean import (
        UnaryBoolExpr, BinaryBoolExpr, TernaryBoolExpr
    )
    from soap.expression.fixpoint import LinkExpr, FixExpr
    if not args:
        if isinstance(op, Variable):
            return op
        if isinstance(op, str):
            return Variable(op)
        raise ValueError(
            'Do not know how to construct expression from {!r}'.format(op))
    if op == operators.FIXPOINT_OP:
        return FixExpr(*args)
    if op == operators.LINK_OP:
        return LinkExpr(*args)
    if op == operators.TERNARY_SELECT_OP:
        return SelectExpr(*args)
    if op in operators.ARITHMETIC_OPERATORS:
        class_list = [UnaryArithExpr, BinaryArithExpr, TernaryArithExpr]
    elif op in operators.BOOLEAN_OPERATORS:
        class_list = [UnaryBoolExpr, BinaryBoolExpr, TernaryBoolExpr]
    else:
        raise ValueError('Unknown operator {}.'.format(op))
    try:
        cls = class_list[len(args) - 1]
    except IndexError:
        raise ValueError('Too many arguments.')
    return cls(op, *args)
