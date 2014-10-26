"""
.. module:: soap.lattice.flat
    :synopsis: The flat lattice.
"""
from soap.lattice.base import Lattice
from soap.lattice.common import _lattice_factory


class FlatLattice(Lattice):
    """A flat lattice structure.

    For example, a flat domain of integers is the following::
                  ⊤
         ...  / / | \ \ ...
        ... -2 -1 0  1 2 ...
         ...  \ \ | / / ...
                  ⊥
    """
    __slots__ = ('value', )

    def __init__(self, value=None, top=False, bottom=False):
        super().__init__(top=top, bottom=bottom)
        if top or bottom:
            return
        self.value = self._cast_value(value)

    def _cast_value(self, value, top=False, bottom=False):
        raise NotImplementedError

    def is_top(self):
        return False

    def is_bottom(self):
        return False

    def join(self, other):
        if other != self:
            return self.__class__(top=True)
        return self

    def meet(self, other):
        if other != self:
            return self.__class__(bottom=True)
        return self

    def le(self, other):
        return self.value == other.value

    def __hash__(self):
        return hash(self.value)

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.value)


def flat(cls=None, name=None):
    """Returns a flat lattice derived from a class `cls`, or a set of elements.

    :param cls: The class to be lifted with a bottom element and crowned with a
        top element.
    :type cls: type
    :param name: The name of the generated class.
    :type name: str
    """
    if not name and callable(cls):
        name = 'FlatLattice_' + cls.__name__
    return _lattice_factory(cls, FlatLattice, name)
