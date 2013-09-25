"""
.. module:: soap.lattice.power
    :synopsis: The power lattice.
"""
from soap.lattice import Lattice
from soap.lattice.common import _lattice_factory


class PowerLattice(Lattice):
    """A lattice structure for powersets.

    For example, the power lattice of the set {1, 2, 3} is the following::
            ⊤ = {1, 2, 3}
          / | \
         /  |  \
    {1,2} {1,3} {2,3}
       | \ / \ / |
       |  x   x  |
       | / \ / \ |
      {1}  {2}  {3}
         \  |  /
          \ | /
            ⊥ = Ø
    """
    def __init__(self, elements=None, top=False, bottom=False):
        super().__init__(top=top, bottom=bottom)
        if top or bottom:
            return
        self.elements = set(self._cast_value(v) for v in elements)

    def _cast_value(self):
        raise NotImplementedError

    def is_top(self):
        return self.elements == self._class()

    def is_bottom(self):
        return len(self.elements) == 0

    def join(self, other):
        return self.__class__(self.elements | other.elements)

    def meet(self, other):
        return self.__class__(self.elements & other.elements)

    def le(self, other):
        return self.elements <= other.elements

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, repr(self.elements))


def power(cls, name=None):
    """Returns a powerset lattice derived from a class `cls`, or a set of
    elements.

    :param cls: The class to be converted to a power lattice.
    :type cls: type
    :param name: The name of the generated class.
    :type name: str
    """
    if not name and callable(cls):
        name = 'PowerLattice_' + cls.__name__
    return _lattice_factory(cls, PowerLattice, name)
