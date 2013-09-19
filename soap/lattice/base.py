import copy


class LatticeMeta(type):
    """The metaclass of lattices.

    It defines the behaviour of the systematic design of lattices."""
    def __mul__(self_class, other_class):
        class ComponentWiseLattice(Lattice):
            def __init__(self, self_class_args=None, other_class_args=None,
                         top=False, bottom=False):
                super().__init__(top=top, bottom=bottom)
                if top or bottom:
                    return
                self.components = []
                class_args = [
                    (self_class, self_class_args),
                    (other_class, other_class_args),
                ]
                for cls, args in class_args:
                    if args == 'top':
                        c = cls(top=True)
                    elif args == 'bottom':
                        c = cls(bottom=True)
                    else:
                        try:
                            c = cls(*args)
                        except (TypeError, ValueError):
                            try:
                                c = cls(args)
                            except (TypeError, ValueError):
                                c = args
                    self.components.append(c)

            def is_top(self):
                t = super().is_top()
                if t is not None:
                    return t
                return all(c.is_top() for c in self.components)

            def is_bottom(self):
                b = super().is_bottom()
                if b is not None:
                    return b
                return all(c.is_bottom() for c in self.components)

            def join(self, other):
                e = super().join(other)
                if e is None:
                    e = copy.copy(self)
                    e.components = [self_comp | other_comp
                                    for self_comp, other_comp in
                                    zip(self.components, other.components)]
                return e

            def meet(self, other):
                e = super().meet(other)
                if e is None:
                    e = copy.copy(self)
                    e.components = [self_comp & other_comp
                                    for self_comp, other_comp in
                                    zip(self.components, other.components)]
                return e

            def __le__(self, other):
                le = super().__le__(other)
                if le is not None:
                    return le
                return all(self_comp <= other_comp
                           for self_comp, other_comp in
                           zip(self.components, other.components))

            def __repr__(self):
                r = super().__repr__()
                if r is not None:
                    return r
                return '%s(%s)' % \
                    (self.__class__.__name__,
                     ', '.join(repr(c) for c in self.components))

        ComponentWiseLattice.__name__ = 'ComponentWiseLattice_%s_%s' % \
            (self_class.__name__, other_class.__name__)
        return ComponentWiseLattice


class Lattice(object, metaclass=LatticeMeta):
    """Common lattice structure.

    Because the partial orders we are using are always complete lattices,
    structures such as preorders, partial orders, dcpos are not implemented.

    Subclasses of this class must implement the member functions:
    :member:`join`, :member:`meet`, :member:`__le__`.
    """
    def __init__(self, *args, top=False, bottom=False, **kwargs):
        if top and bottom:
            raise ValueError(
                'Lattice element cannot be bottom and top simultaneously.')
        self.top = top
        self.bottom = bottom

    def is_top(self):
        if self.top:
            return True
        if self.bottom:
            return False

    def is_bottom(self):
        if self.top:
            return False
        if self.bottom:
            return True

    def _check_type_consistency(self, other):
        if self.__class__ == other.__class__:
            return
        raise TypeError('Inconsistent lattice types: %s, %s' % (self, other))

    def join(self, other):
        self._check_type_consistency(other)
        if self.is_top() or other.is_bottom():
            return self
        if self.is_bottom() or other.is_top():
            return other

    def meet(self, other):
        self._check_type_consistency(other)
        if self.is_top() or other.is_bottom():
            return other
        if self.is_bottom() or other.is_top():
            return self

    def __le__(self, other):
        self._check_type_consistency(other)
        if self.is_bottom():
            return True
        if other.is_top():
            return True
        if self.is_top() and not other.is_top():
            return False

    def __ge__(self, other):
        return other.__le__(self)

    def __eq__(self, other):
        """Defaults to antisymmetry."""
        return self.__le__(other) and self.__ge__(other)

    def __or__(self, other):
        return self.join(other)
    __ror__ = __or__

    def __and__(self, other):
        return self.meet(other)
    __rand__ = __and__

    def __str__(self):
        if self.is_top():
            return '⊤'
        if self.is_bottom():
            return '⊥'

    def __repr__(self):
        if self.is_top():
            return self.__class__.__name__ + '(top=True)'
        if self.is_bottom():
            return self.__class__.__name__ + '(bottom=True)'
