from itertools import zip_longest

from soap.lattice.base import Lattice
from soap.lattice.common import _lattice_factory


class ListLattice(Lattice, list):
    """Defines a lattice for lists."""
    __slots__ = ()

    def __init__(self, iterable=None, top=False, bottom=False):
        super().__init__(top=top, bottom=bottom)
        if top:
            return
        if bottom:
            iterable = []
        iterable = [self._cast_value(i) for i in iterable]
        while iterable and iterable[-1].is_bottom():
            iterable.pop()
        list.__init__(self, iterable)

    def _cast_value(self, value, top=False, bottom=False):
        raise NotImplementedError

    def is_top(self):
        return any(i.is_top() for i in self)

    def is_bottom(self):
        return all(i.is_bottom() for i in self)

    def le(self, other):
        for j, k in zip(self, other):
            if j <= k:
                continue
            return False
        return True

    def meet(self, other):
        return self.__class__((j & k for j, k in zip(self, other)))

    def join(self, other):
        zipper = zip_longest(
            self, other, fillvalue=self._cast_value(bottom=True))
        return self.__class__((j & k for j, k in zipper))

    def __add__(self, other):
        if self.is_top() or other.is_bottom():
            return self
        if self.is_bottom() or other.is_top():
            return other
        return self.__class__(list.__add__(self, other))

    def __getitem__(self, item):
        if self.is_top():
            return self._cast_value(top=True)
        if isinstance(item, slice):
            raise NotImplementedError('slicing is not required...yet')
        try:
            return self.__class__(list.__getitem__(self, item))
        except IndexError:
            return self._cast_value(bottom=True)


def list(cls=None, name=None):
    """Returns a list lattice in which elements are derived from a lattice
    class `cls`, or a set of elements.

    :param cls: The class to be contained in the list sequence.
    :type cls: type
    :param name: The name of the generated class.
    :type name: str
    """
    if not name and callable(cls):
        name = 'ListLattice_' + cls.__name__
    return _lattice_factory(cls, ListLattice, name)
