"""
.. module:: soap.expression.variable
    :synopsis: The class of variables.
"""
from soap.common.cache import Flyweight


class Variable(Flyweight):
    """The variable class."""

    __slots__ = ('name')

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return '{cls}({name!r})'.format(
            cls=self.__class__.__name__, name=self.name)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)
