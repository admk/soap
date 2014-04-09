import abc
import copy


class UnifiedSummationLattice(object):
    """Defines a summation of two partial orders with unified top and
    bottom elements."""

    __slots__ = ('v', )
    self_class = other_class = None

    def __init__(self, *args, top=False, bottom=False, **kwargs):
        super().__init__(top=top, bottom=bottom)
        if top or bottom:
            return
        for c in (self.self_class, self.other_class):
            v = self._try_class(c, *args, **kwargs)
            if v is not NotImplemented:
                break
        self.v = v

    def _try_class(self, cls, *args, **kwargs):
        if len(args) == 1:
            if isinstance(args[0], cls):
                return cls
        return cls(*args, **kwargs)

    def is_top(self):
        return self.v.is_top()

    def is_bottom(self):
        return self.v.is_bottom()

    def _type_check(self, other):
        self_type, other_type = type(self.v), type(other.v)
        return self_type is other_type

    def join(self, other):
        if not self._type_check(other):
            return self.__class__(top=True)
        return self.v | other.v

    def meet(self, other):
        if not self._type_check(other):
            return self.__class__(bottom=True)
        return self.v & other.v

    def le(self, other):
        if not self._type_check(other):
            return False
        return self.v <= other.v

    def __str__(self):
        return str(self.v)

    def __repr__(self):
        return '{cls}({value!r})'.format(
            cls=self.__class__.__name__, value=self.v)


class ComponentWiseLattice(object):
    """Defines a component-wise partial order."""
    __slots__ = ('_components', )
    _component_classes = None

    def __init__(self, *components, top=False, bottom=False):
        components = tuple(
            cls(bottom=True) if c is None else c
            for c, cls in zip(components, self._component_classes))
        super().__init__(top=top, bottom=bottom)
        if top or bottom:
            return
        self._components = components

    @property
    def components(self):
        if self.top or self.bottom:
            return tuple(cls(top=self.top, bottom=self.bottom)
                         for cls in self._component_classes)
        return self._components

    @components.setter
    def components(self, value):
        self._components = value

    def is_top(self):
        return all(c.is_top() for c in self.components)

    def is_bottom(self):
        return all(c.is_bottom() for c in self.components)

    def join(self, other):
        e = copy.copy(self)
        e.components = [self_comp | other_comp
                        for self_comp, other_comp in
                        zip(self.components, other.components)]
        return e

    def meet(self, other):
        e = copy.copy(self)
        e.components = [self_comp & other_comp
                        for self_comp, other_comp in
                        zip(self.components, other.components)]
        return e

    def le(self, other):
        return all(self_comp <= other_comp
                   for self_comp, other_comp in
                   zip(self.components, other.components))

    def __hash__(self):
        return hash((self.__class__, self.components))

    def __str__(self):
        return '({})'.format(','.join(str(c) for c in self.components))

    def __repr__(self):
        components = ', '.join(repr(c) for c in self.components)
        return '{cls}({components})'.format(
            cls=self.__class__.__name__, components=components)


class LatticeMeta(abc.ABCMeta):
    """
    The metaclass of lattices.

    It defines the behaviour of the systematic design of lattices.
    """
    def __add__(self, other):
        from soap.lattice.base import Lattice

        class SumLat(UnifiedSummationLattice, Lattice):
            __slots__ = ()
            self_class = self
            other_class = other

        SumLat.__name__ = 'UnifiedSummationLattice_{}_{}'.format(
            self.__name__, other.__name__)
        return SumLat

    def __mul__(self, other):
        from soap.lattice.base import Lattice

        class CompLat(ComponentWiseLattice, Lattice):
            __slots__ = ()
            _component_classes = (self, other)

        CompLat.__name__ = 'ComponentWiseLattice_{}_{}'.format(
            self.__name__, other.__name__)
        return CompLat
