"""
.. module:: soap.expression.variable
    :synopsis: The class of variables.
"""
from soap.expression.base import UnaryExpression
from soap.expression.arithmetic import ArithmeticMixin
from soap.expression.boolean import BooleanMixin


class Variable(ArithmeticMixin, BooleanMixin, UnaryExpression):
    """The variable class."""

    __slots__ = ()

    def __init__(self, name=None, top=False, bottom=False):
        super().__init__(
            op=None, a=name, top=top, bottom=bottom, _check_args=False)
        if top or bottom:
            return

    @property
    def name(self):
        return self.a

    def _cast_value(self, value, top=False, bottom=False):
        return value

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return '{cls}({name!r})'.format(
            cls=self.__class__.__name__, name=self.name)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.name == other.name

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self.name, self.__class__))


class FreeVariable(Variable):
    __slots__ = ()

    def __str__(self):
        return '${}'.format(self.name)


class ExpandableVariable(Variable):
    """A free variable, must be substituted before evaluating for its value."""

    __slots__ = ('expr')

    def __init__(self, name=None, expr=None, top=False, bottom=False):
        if isinstance(name, FreeVariable):
            name = name.name
        super().__init__(name=name, top=top, bottom=bottom)
        if top or bottom:
            return
        self.expr = expr

    @property
    def variable(self):
        return FreeVariable(self.name)

    def __str__(self):
        return '[{var} ↦ {expr}]'.format(var=self.variable, expr=self.expr)

    def __repr__(self):
        return '{cls}({var!r}, {expr!r})'.format(
            cls=self.__class__.__name__, var=self.variable, expr=self.expr)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.name == other.name and self.expr == other.expr

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self.name, self.expr, self.__class__))
