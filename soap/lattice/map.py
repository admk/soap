"""
.. module:: soap.lattice.map
    :synopsis: The mapping lattice.
"""
from soap.lattice import Lattice
from soap.lattice.common import _lattice_factory


class MapLattice(Lattice, dict):
    """Defines a lattice for mappings/functions."""
    def __init__(self, mapping=None, top=False, bottom=False, **kwargs):
        super().__init__(top=top, bottom=bottom)
        self.update(mapping or {}, **kwargs)
        for k, v in list(self.items()):
            if type(v) is str:
                if v == 'bottom':
                    del self[k]
                    continue
                elif v == 'top':
                    v = self._cast_value(top=True)
            else:
                v = self._cast_value(v)
            self[k] = v

    def _cast_value(self, v=None, top=False, bottom=False):
        raise NotImplementedError

    def is_top(self):
        return False

    def is_bottom(self):
        return all(v.is_bottom() for _, v in self.items())

    def join(self, other):
        join_dict = dict(self)
        for k in other:
            if k in self:
                join_dict[k] = self[k] | other[k]
            else:
                join_dict[k] = other[k]
        return self.__class__(mapping=join_dict)

    def meet(self, other):
        meet_dict = {}
        for k in list(self) + list(other):
            if k not in self or k not in other:
                continue
            v = self[k] & other[k]
            if not v.is_bottom():
                meet_dict[k] = v
        return self.__class__(mapping=meet_dict)

    def le(self, other):
        for k, v in self.items():
            if k not in other:
                return False
            if not v <= other[k]:
                return False
        return True

    def __getitem__(self, key):
        if self.is_top():
            return self._cast_value(top=True)
        if not self.is_bottom() and key in self:
            return super().__getitem__(key)
        return self._cast_value(bottom=True)

    def __str__(self):
        return '[%s]' % ', '.join(
            str(k) + '↦' + str(v) for k, v in self.items())

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, dict(self))


def map(from_cls, to_lattice, name=None):
    """Returns a mapping lattice which orders the partial maps from a class
    `from_cls` to a lattice `to_lattice`.

    :param from_cls: The domain of the function.
    :type cls: type
    :param to_lattice: The range of the function, must be a lattice.
    :type name: :class:`soap.lattice.Lattice`
    """
    if not name:
        try:
            to_lattice_name = to_lattice.__name__
        except AttributeError:
            to_lattice_name = type(to_lattice).__name__
        name = 'MapLattice_%s_to_%s' % (from_cls.__name__, to_lattice_name)
    return _lattice_factory(to_lattice, MapLattice, name)
