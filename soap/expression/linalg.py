from soap.expression.arithmetic import ArithmeticMixin
from soap.expression.base import BinaryExpression, TernaryExpression
from soap.expression.boolean import BooleanMixin
from soap.expression.operators import INDEX_ACCESS_OP, INDEX_UPDATE_OP


class AccessExpr(ArithmeticMixin, BooleanMixin, BinaryExpression):

    __slots__ = ()

    def __init__(self, var=None, subscript=None, top=False, bottom=False):
        super().__init__(
            op=INDEX_ACCESS_OP, a1=var, a2=tuple(subscript),
            top=top, bottom=bottom)

    @property
    def var(self):
        return self.a1

    @property
    def subscript(self):
        return self.a2

    def __str__(self):
        return '{}[{}]'.format(self.var, self.subscript)

    def __repr__(self):
        return '{cls}({var!r}, {subscript!r})'.format(
            cls=self.__class__.__name__, var=self.var,
            subscript=self.subscript)


class UpdateExpr(ArithmeticMixin, BooleanMixin, TernaryExpression):

    __slots__ = ()

    def __init__(
            self, var=None, subscript=None, expr=None,
            top=False, bottom=False):
        super().__init__(
            op=INDEX_UPDATE_OP, a1=var, a2=tuple(subscript), a3=expr,
            top=top, bottom=bottom)

    @property
    def var(self):
        return self.a1

    @property
    def subscript(self):
        return self.a2

    @property
    def expr(self):
        return self.a3

    def __str__(self):
        return 'update({}, {}, {})'.format(self.var, self.subscript, self.expr)

    def __repr__(self):
        return '{cls}({var!r}, {subscript!r}, {expr!r})'.format(
            cls=self.__class__.__name__, var=self.var,
            subscript=self.subscript, expr=self.expr)
