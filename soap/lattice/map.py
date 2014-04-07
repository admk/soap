"""
.. module:: soap.lattice.map
    :synopsis: The mapping lattice.
"""
import copy

from soap.lattice import Lattice
from soap.lattice.common import _lattice_factory


class MapLattice(Lattice, dict):
    """Defines a lattice for mappings/functions."""
    __slots__ = ()

    def __init__(self, mapping=None, top=False, bottom=False, **kwargs):
        super().__init__(top=top, bottom=bottom)
        if top or bottom:
            return
        d = dict(mapping or {}, **kwargs)
        for k, v in d.items():
            k = self._cast_key(k)
            v = self._cast_value(v)
            if not v.is_bottom():
                self[k] = v

    def _cast_key(self, k):
        raise NotImplementedError

    def _cast_value(self, v=None, top=False, bottom=False):
        raise NotImplementedError

    def is_top(self):
        return False

    def is_bottom(self):
        return all(v.is_bottom() for v in self.values())

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

    def __contains__(self, key):
        return super().__contains__(self._cast_key(key))

    def __getitem__(self, key):
        if self.is_top():
            return self._cast_value(top=True)
        if isinstance(key, slice):
            new_map = copy.deepcopy(self)
            new_map.__setitem__(key.start, key.stop)
            return new_map
        if self.is_bottom():
            return self._cast_value(bottom=True)
        try:
            return super().__getitem__(self._cast_key(key))
        except KeyError:
            return self._cast_value(bottom=True)

    def __setitem__(self, key, value):
        key = self._cast_key(key)
        value = self._cast_value(value)
        if value.is_bottom():
            if key in self:
                del self[key]
            return
        super().__setitem__(key, value)

    def __delitem__(self, key):
        super().__delitem__(self._cast_key(key))

    def __str__(self):
        return '{{{}}}'.format(', '.join(
            '{key} ↦ {value}'.format(key=k, value=v) for k, v in self.items()))

    def __repr__(self):
        return '{cls}({items!r})'.format(
            cls=self.__class__.__name__, items=dict(self))


def map(from_cls=None, to_lattice=None, name=None):
    """Returns a mapping lattice which orders the partial maps from a class
    `from_cls` to a lattice `to_lattice`.

    :param from_cls: The domain of the function.
    :type cls: type
    :param to_lattice: The range of the function, must be a lattice.
    :type name: :class:`soap.lattice.Lattice`
    """
    if not name and from_cls and to_lattice:
        try:
            to_lattice_name = to_lattice.__name__
        except AttributeError:
            to_lattice_name = type(to_lattice).__name__
        name = 'MapLattice_{}_to_{}'.format(from_cls.__name__, to_lattice_name)
    cls = _lattice_factory(to_lattice, MapLattice, name)
    if from_cls:
        cls._cast_key = lambda self, key: from_cls(key)
    return cls
