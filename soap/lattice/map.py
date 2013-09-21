"""
.. module:: soap.lattice.map
    :synopsis: The mapping lattice.
"""
from soap.lattice import Lattice
from soap.lattice.common import _lattice_factory


class MapLattice(Lattice):
    """Defines a lattice for mappings/functions."""
    def __init__(self, mapping=None, top=False, bottom=False, **kwargs):
        super().__init__(top=top, bottom=bottom)
        self.mapping = dict(mapping or {}, **kwargs)
        for k, v in list(self.mapping.items()):
            if type(v) is str:
                if v == 'bottom':
                    del self.mapping[k]
                    continue
                elif v == 'top':
                    v = self._class()(top=True)
            elif type(v) is not self._class():
                v = self._class()(v)
            self.mapping[k] = v

    def _class(self):
        pass

    def is_top(self):
        return False

    def is_bottom(self):
        return all(v.is_bottom() for _, v in self.mapping.items())

    def join(self, other):
        join_dict = dict(self.mapping)
        for k in other.mapping:
            if k in self.mapping:
                join_dict[k] = self.mapping[k] | other.mapping[k]
            else:
                join_dict[k] = other.mapping[k]
        return self.__class__(mapping=join_dict)

    def meet(self, other):
        meet_dict = {}
        for k in list(self.mapping) + list(other.mapping):
            if k not in self.mapping or k not in other.mapping:
                continue
            v = self.mapping[k] & other.mapping[k]
            if not v.is_bottom():
                meet_dict[k] = v
        return self.__class__(mapping=meet_dict)

    def le(self, other):
        for k, v in self.mapping.items():
            if k not in other.mapping:
                return False
            if not v <= other.mapping[k]:
                return False
        return True

    def __str__(self):
        return '[%s]' % ', '.join(
            str(k) + '↦' + str(v) for k, v in self.mapping.items())

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.mapping)


def map(from_cls, to_lattice, name=None):
    """Returns a mapping lattice which orders the partial maps from a class
    `from_cls` to a lattice `to_lattice`.

    :param from_cls: The domain of the function.
    :type cls: type
    :param to_lattice: The range of the function, must be a lattice.
    :type name: :class:`soap.lattice.Lattice`
    """
    if not name:
        name = 'MapLattice_%s_to_%s' % (from_cls.__name__, to_lattice.__name__)
    return _lattice_factory(to_lattice, MapLattice, name)
