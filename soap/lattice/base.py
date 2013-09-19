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

            def le(self, other):
                le = super().le(other)
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
    :member:`join`, :member:`meet`, :member:`le`.
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
        raise TypeError(
            'Inconsistent lattice types: %s, %s' %
            (str(self.__class__), str(other.__class__)))

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

    def le(self, other):
        self._check_type_consistency(other)
        if self.is_bottom():
            return True
        if other.is_top():
            return True
        if self.is_top() and not other.is_top():
            return False

    __or__ = lambda self, other: self.join(other)
    __ror__ = lambda self, other: self.join(other)
    __and__ = lambda self, other: self.meet(other)
    __rand__ = lambda self, other: self.meet(other)

    __le__ = lambda self, other: self.le(other)
    __eq__ = lambda self, other: self.le(other) and other.le(self)
    __ne__ = lambda self, other: not self.le(other) or not other.le(self)
    __ge__ = lambda self, other: other.le(self)
    __lt__ = lambda self, other: not other.le(self)
    __gt__ = lambda self, other: not self.le(other)

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
