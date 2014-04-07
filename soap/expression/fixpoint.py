from soap.expression import operators
from soap.expression.arithmetic import ArithExpr
from soap.expression.base import UnaryExpression, BinaryExpression
from soap.expression.boolean import BoolExpr
from soap.expression.variable import ExpandableVariable


class LinkExpression(BinaryExpression):
    __slots__ = ()

    def __init__(self, a1=None, a2=None, top=False, bottom=False):
        super().__init__(operators.LINK_OP, a1, a2, top=top, bottom=bottom)
        # TODO validate a1 is a free variable
        # TODO validate a2 is a state


class LinkBoolExpr(LinkExpression, BoolExpr):
    __slots__ = ()


class LinkArithExpr(LinkExpression, ArithExpr):
    __slots__ = ()


class FixpointExpr(UnaryExpression):
    """
    Fixpoint expression.

    An object of this class consists of an operator 'fix', and an argument
    which is an ExpandableVariable instance that models the fixpoint funtion.
    """
    def __init__(self, a=None, top=False, bottom=False):
        super().__init__(operators.FIXPOINT_OP, a, top=top, bottom=bottom)
        if top or bottom:
            return
        if not isinstance(a, ExpandableVariable):
            raise TypeError('Argument must be an ExpandableVariable instance.')
