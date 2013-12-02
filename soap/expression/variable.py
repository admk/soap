"""
.. module:: soap.expression.variable
    :synopsis: The class of variables.
"""
from soap.common.cache import Flyweight
from soap.common.label import Label


class Variable(Flyweight):
    """The variable class."""

    __slots__ = ('name', 'label')

    def __init__(self, name, label=None):
        self.name = name
        self.label = label or Label(name)

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return '{cls}({name!r}, {label!r})'.format(
            cls=self.__class__.__name__, name=self.name, label=self.label)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)
