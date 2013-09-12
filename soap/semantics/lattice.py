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
                if not e:
                    e = copy.copy(self)
                    e.components = [self_comp | other_comp
                                    for self_comp, other_comp in
                                    zip(self.components, other.components)]
                return e

            def meet(self, other):
                e = super().meet(other)
                if not e:
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

    def _is_consistent_type(self, other):
        return self.__class__ == other.__class__

    def join(self, other):
        if not self._is_consistent_type(other):
            raise TypeError('Inconsistent lattice types')
        if self.is_top() or other.is_bottom():
            return self
        if self.is_bottom() or other.is_top():
            return other

    def meet(self, other):
        if not self._is_consistent_type(other):
            raise TypeError('Inconsistent lattice types')
        if self.is_top() or other.is_bottom():
            return other
        if self.is_bottom() or other.is_top():
            return self

    def __le__(self, other):
        if not self._is_consistent_type(other):
            raise TypeError('Inconsistent lattice types')
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

    def __and__(self, other):
        return self.meet(other)

    def __repr__(self):
        if self.is_top():
            return self.__class__.__name__ + '(Top)'
        if self.is_bottom():
            return self.__class__.__name__ + '(Bottom)'


class FlatLattice(Lattice):
    """A flat lattice structure.

    For example, a flat domain of integers is the following::
                  ⊤
         ...  / / | \ \ ...
        ... -2 -1 0  1 2 ...
         ...  \ \ | / / ...
                  ⊥
    """
    def __init__(self, var=None, top=False, bottom=False):
        super().__init__(top=top, bottom=bottom)
        if top or bottom:
            return
        if self._class():
            self.v = self._class()(var)
        else:
            if not var in self._container():
                raise ValueError('Non-existing element: %s' % repr(var))
            self.v = var

    def _class(self):
        pass

    def _container(self):
        pass

    def is_top(self):
        t = super().is_top()
        if t is not None:
            return t
        return False

    def is_bottom(self):
        b = super().is_bottom()
        if b is not None:
            return b
        return False

    def join(self, other):
        e = super().join(other)
        if e:
            return e
        if other != self:
            return self.__class__(top=True)
        return self

    def meet(self, other):
        e = super().meet(other)
        if e:
            return e
        if other != self:
            return self.__class__(bottom=True)
        return self

    def __le__(self, other):
        le = super().__le__(other)
        if le is not None:
            return le
        return self == other

    def __eq__(self, other):
        if self.is_top() and other.is_top():
            return True
        if self.is_bottom() and other.is_bottom():
            return True
        try:
            return self.v == other.v
        except AttributeError:
            return False

    def __repr__(self):
        r = super().__repr__()
        if r is not None:
            return r
        return '%s(%s)' % (self.__class__.__name__, repr(self.v))




def _is_class(cls):
    try:
        class _(cls):
            pass
        return True
    except TypeError:
        return False


def _lattice_factory(cls, lattice_cls, name):
    class L(lattice_cls):
        def _class(self):
            if _is_class(cls):
                return cls

        def _container(self):
            if not _is_class(cls):
                return cls
    if name:
        L.__name__ = name
    return L


def flat(cls, name=None):
    """Returns a flat domain derived from a class `cls`, or a set of elements.
    """
    if not name and _is_class(cls):
        name = 'FlatLattice_' + cls.__name__
    return _lattice_factory(cls, FlatLattice, name)


def power(cls, name=None):
    """Returns a powerset domain derived from a class `cls`, or a set of
    elements.
    """
    if not name and _is_class(cls):
        name = 'PowerLattice_' + cls.__name__
    return _lattice_factory(cls, PowerLattice, name)
