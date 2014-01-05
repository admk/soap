"""
.. module:: soap.expression.variable
    :synopsis: The class of variables.
"""
from soap.common.cache import Flyweight
from soap.lattice.flat import FlatLattice


class Variable(FlatLattice, Flyweight):
    """The variable class."""

    __slots__ = ('name')

    def __init__(self, name=None, top=False, bottom=False):
        super().__init__(top=top, bottom=bottom)
        if top or bottom:
            return
        self.name = name

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
        return hash(self.name)
