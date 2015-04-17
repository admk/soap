from soap.expression.arithmetic import ArithmeticMixin
from soap.expression.base import (
    BinaryExpression, Expression, TernaryExpression
)
from soap.expression.common import is_variable
from soap.expression.boolean import BooleanMixin
from soap.expression.operators import (
    INDEX_ACCESS_OP, INDEX_UPDATE_OP, SUBSCRIPT_OP
)


class Subscript(Expression):

    __slots__ = ()

    def __init__(self, *subscript):
        super().__init__(SUBSCRIPT_OP, *subscript)

    def __iter__(self):
        return iter(self.args)

    def __str__(self):
        return '[{}]'.format(', '.join(self._args_to_str()))

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self.args)


class _TrueVarMixin(object):
    def true_var(self):
        var = self.var
        while not is_variable(var):
            var = var.var
        return var


class AccessExpr(
        ArithmeticMixin, BooleanMixin, BinaryExpression, _TrueVarMixin):

    __slots__ = ()

    def __init__(self, var, subscript):
        from soap.semantics.label import Label
        if not isinstance(subscript, Label):
            subscript = Subscript(*subscript)
        super().__init__(INDEX_ACCESS_OP, var, subscript)

    @property
    def var(self):
        return self.a1

    @property
    def subscript(self):
        return self.a2

    def __str__(self):
        return '{}{}'.format(self.var, self.subscript)

    def __repr__(self):
        return '{cls}({var!r}, {subscript!r})'.format(
            cls=self.__class__.__name__, var=self.var,
            subscript=self.subscript)


class UpdateExpr(
        ArithmeticMixin, BooleanMixin, TernaryExpression, _TrueVarMixin):

    __slots__ = ()

    def __init__(self, var, subscript, expr):
        from soap.semantics.label import Label
        if not isinstance(subscript, Label):
            subscript = Subscript(*subscript)
        super().__init__(INDEX_UPDATE_OP, var, subscript, expr)

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
