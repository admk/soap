from soap.lattice.base import Lattice


class UnifiedSummationLattice(Lattice):
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
