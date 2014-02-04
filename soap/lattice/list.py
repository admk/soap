import builtins
from itertools import zip_longest

from soap.lattice.base import Lattice
from soap.lattice.common import _lattice_factory


class ListLattice(Lattice):
    """Defines a lattice for lists."""
    __slots__ = ()

    def __init__(self, iterable=None, top=False, bottom=False):
        super().__init__(top=top, bottom=bottom)
        if top or bottom:
            return
        iterable = [self._cast_value(i) for i in iterable]
        while iterable and iterable[-1].is_bottom():
            iterable.pop()
        self.list = tuple(iterable)

    def _cast_value(self, value=None, top=False, bottom=False):
        raise NotImplementedError

    def is_top(self):
        return False

    def is_bottom(self):
        return all(i.is_bottom() for i in self)

    _zipper = lambda self, other: zip_longest(
        self, other, fillvalue=self._cast_value(bottom=True))

    def le(self, other):
        for j, k in self._zipper(other):
            if j <= k:
                continue
            return False
        return True

    def meet(self, other):
        return self.__class__((j & k for j, k in self._zipper(other)))

    def join(self, other):
        return self.__class__((j | k for j, k in self._zipper(other)))

    def append(self, item):
        if self.is_top():
            return self
        l = [] if self.is_bottom() else self.list
        return self.__class__(l + [self._cast_value(item)])

    def __len__(self):
        return len(self.list)

    def __iter__(self):
        return iter(self.list)

    def __contains__(self, item):
        return item in self.list

    def __getitem__(self, index):
        if self.is_top():
            return self._cast_value(top=True)
        if self.is_bottom():
            return self._cast_value(bottom=True)
        if isinstance(index, slice):
            raise NotImplementedError('slicing is not required...yet')
        try:
            return self.list[index]
        except IndexError:
            return self._cast_value(bottom=True)

    def __hash__(self):
        return hash((self.__class__, self.list))

    def __str__(self):
        return str(builtins.list(self.list))

    def __repr__(self):
        return '{cls}({list})'.format(
            cls=self.__class__.__name__, list=builtins.list(self.list))


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
