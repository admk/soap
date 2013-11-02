"""
.. module:: soap.expression.variable
    :synopsis: The class of variables.
"""
from soap.common import Flyweight, Comparable


class Variable(Flyweight, Comparable):
    """The variable class."""

    __slots__ = ('n', )

    def __init__(self, name):
        self.n = name

    def __str__(self):
        return str(self.n)

    def __repr__(self):
        return '{cls}({name!r})'.format(
            cls=self.__class__.__name__, name=self.n)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.n == other.n

    def __lt__(self, other):
        if not isinstance(other, Variable):
            return False
        return self.n < other.n

    def __hash__(self):
        return hash(self.n)
