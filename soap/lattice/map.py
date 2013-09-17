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
        t = super().is_top()
        return False if t is None else t

    def is_bottom(self):
        b = super().is_bottom()
        if b is not None:
            return b
        non_bottoms = [_ for _, v in self.mapping.items()
                       if not v.is_bottom()]
        if len(non_bottoms) == 0:
            return True

    def join(self, other):
        e = super().join(other)
        if e:
            return e
        join_dict = dict(self.mapping)
        for k in other.mapping:
            if k in self.mapping:
                join_dict[k] = self.mapping[k] | other.mapping[k]
            else:
                join_dict[k] = other.mapping[k]
        print(join_dict)
        return self.__class__(mapping=join_dict)

    def meet(self, other):
        e = super().meet(other)
        if e:
            return e
        meet_dict = {}
        for k in list(self.mapping) + list(other.mapping):
            if k not in self.mapping or k not in other.mapping:
                continue
            v = self.mapping[k] & other.mapping[k]
            if not v.is_bottom():
                meet_dict[k] = v
        return self.__class__(mapping=meet_dict)

    def __le__(self, other):
        le = super().__le__(other)
        if le is not None:
            return le
        for k, v in self.mapping.items():
            if k not in other.mapping:
                return False
            if not v <= other.mapping[k]:
                return False
        return True

    def __repr__(self):
        r = super().__repr__()
        if r is not None:
            return r
        return '%s(%s)' % (self.__class__.__name__, repr(self.mapping))


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
