from soap.lattice.base import Lattice
from soap.lattice.common import _lattice_factory


class ReversedLattice(Lattice):
    def __init__(self, *args, lattice=None, top=False, bottom=False, **kwargs):
        super().__init__(top=top, bottom=bottom)
        if top or bottom:
            return
        if lattice:
            self.lattice = lattice
        else:
            self.lattice = self._class()(*args, **kwargs)

    def _class(self):
        raise NotImplementedError

    def is_top(self):
        return self.lattice.is_bottom()

    def is_bottom(self):
        return self.lattice.is_top()

    def le(self, other):
        return self.lattice >= other.lattice

    def join(self, other):
        return self.__class__(lattice=(self.lattice & other.lattice))

    def meet(self, other):
        return self.__class__(lattice=(self.lattice | other.lattice))

    def __hash__(self, other):
        return hash(self.lattice)

    def __str__(self):
        return 'r<{}>'.format(self.lattice)

    def __repr__(self):
        return '{cls}(lattice={lat})'.format(
            cls=self.__class__.__name__, lat=self.lattice)


def reversed(cls, name=None):
    if not name and callable(cls):
        name = 'ReversedLattice_' + cls.__name__
    return _lattice_factory(cls, ReversedLattice, name)
