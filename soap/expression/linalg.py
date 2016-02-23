from soap.common.formatting import indent
from soap.expression.arithmetic import ArithmeticMixin
from soap.expression import (
    BinaryExpression, Expression, TernaryExpression, FixExpr
)
from soap.expression.common import is_variable
from soap.expression.boolean import BooleanMixin
from soap.expression.operators import (
    INDEX_ACCESS_OP, INDEX_UPDATE_OP, SUBSCRIPT_OP
)


class Subscript(Expression):
    __slots__ = ()
    _str_brackets = False

    def __init__(self, *subscript):
        super().__init__(SUBSCRIPT_OP, *subscript)

    def __iter__(self):
        return iter(self.args)

    def format(self):
        return ''.join('[' + a.format() + ']' for a in self.args)

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self.args)


class _TrueVarMixin(object):
    __slots__ = ()

    def true_var(self):
        var = self.var
        while not is_variable(var):
            if isinstance(var, FixExpr):
                var = var.loop_var
            else:
                var = var.var
        return var


class AccessExpr(
        ArithmeticMixin, BooleanMixin, BinaryExpression, _TrueVarMixin):
    __slots__ = ()
    _str_brackets = False

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

    def format(self):
        var, subscript = self._args_to_str()
        return '{}{}'.format(var, subscript)

    def __repr__(self):
        return '{cls}({var!r}, {subscript!r})'.format(
            cls=self.__class__.__name__, var=self.var,
            subscript=self.subscript)


class UpdateExpr(
        ArithmeticMixin, BooleanMixin, TernaryExpression, _TrueVarMixin):
    __slots__ = ()
    _str_brackets = False

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

    def format(self):
        var, subscript, expr = (a.format() for a in self.args)
        args = '{}, \n{}, \n{}'.format(var, subscript, expr)
        return 'update(\n{})'.format(indent(args))

    def __repr__(self):
        return '{cls}({var!r}, {subscript!r}, {expr!r})'.format(
            cls=self.__class__.__name__, var=self.var,
            subscript=self.subscript, expr=self.expr)
