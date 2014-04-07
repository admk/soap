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
        super().__init__(op=None, a=name, top=top, bottom=bottom)

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


def _underline(text):
    combining_low_line = '\u0332'
    return combining_low_line.join(list(text)) + combining_low_line


class FreeFlowVar(Variable):
    """A free variable, must be substituted before evaluating for its value."""
    __slots__ = ('flow', 'expr')

    def __init__(self, name=None, flow=None, top=False, bottom=False):
        name = '{name}{label}'.format(name=name, label=flow.label.label_value)
        super().__init__(name=name, top=top, bottom=bottom)

    def __str__(self):
        return _underline('{}'.format(self.name))
