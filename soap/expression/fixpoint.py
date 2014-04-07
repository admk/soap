from soap.expression import operators
from soap.expression.arithmetic import BinaryArithExpr


class LinkExpr(BinaryArithExpr):
    __slots__ = ()

    def __init__(self, a1=None, a2=None, top=False, bottom=False):
        super().__init__(operators.LINK_OP, a1, a2, top=top, bottom=bottom)
        # TODO validate a1 is a free variable
        # TODO validate a2 is a state

    def __str__(self):
        expr, state = self._args_to_str()
        return '{expr} % {state}'.format(expr=expr, state=state)

    def __repr__(self):
        return '{cls}({a1!r}, {a2!r})'.format(
            cls=self.__class__.__name__, a1=self.a1, a2=self.a2)


class FixExpr(BinaryArithExpr):
    """Fixpoint expression."""

    def __init__(self, a1=None, a2=None, top=False, bottom=False):
        super().__init__(operators.FIXPOINT_OP, a1, a2, top=top, bottom=bottom)
        if top or bottom:
            return
        # TODO a1 : free var
        # TODO a2 : fix expr?
        a1.expr = a2

    def __str__(self):
        return '{op}[{a1} ↦ {a2}]'.format(op=self.op, a1=self.a1, a2=self.a2)
