from copy import copy

from soap.lattice.base import Lattice


class ComponentWiseLattice(Lattice):
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

    def __iter__(self):
        return iter(self.components)

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
        e = copy(self)
        e.components = [self_comp | other_comp
                        for self_comp, other_comp in
                        zip(self.components, other.components)]
        return e

    def meet(self, other):
        e = copy(self)
        e.components = [self_comp & other_comp
                        for self_comp, other_comp in
                        zip(self.components, other.components)]
        return e

    def le(self, other):
        return all(self_comp <= other_comp
                   for self_comp, other_comp in
                   zip(self.components, other.components))

    def __hash__(self):
        return hash(self.components)

    def __str__(self):
        return '({})'.format(','.join(str(c) for c in self.components))

    def __repr__(self):
        components = ', '.join(repr(c) for c in self.components)
        return '{cls}({components})'.format(
            cls=self.__class__.__name__, components=components)
