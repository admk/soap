class LatticeMeta(type):
    """The metaclass of lattices.

    It defines the behaviour of the systematic design of lattices."""
    def __mul__(self_class, other_class):
        class ComponentWiseLattice(Lattice):
            def __init__(self, self_class_args, other_class_args):
                if self_class_args == 'top':
                    self.c1 = top(self_class)
                elif self_class_args == 'bottom':
                    self.c1 = bottom(self_class)
                else:
                    try:
                        self.c1 = self_class(*self_class_args)
                    except (TypeError, ValueError):
                        self.c1 = self_class(self_class_args)
                if other_class_args == 'top':
                    self.c2 = top(other_class)
                elif other_class_args == 'bottom':
                    self.c2 = bottom(other_class)
                else:
                    try:
                        self.c2 = other_class(*other_class_args)
                    except (TypeError, ValueError):
                        self.c2 = other_class(other_class_args)

            def __le__(self, other):
                return (self.c1 <= other.c1) and (self.c2 <= other.c2)

            def __repr__(self):
                return '%s(%s, %s)' % \
                    (self.__class__.__name__, repr(self.c1), repr(self.c2))
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
    def join(self, other):
        raise NotImplementedError

    def meet(self, other):
        raise NotImplementedError

    def __le__(self, other):
        raise NotImplementedError

    def __ge__(self, other):
        return other.__le__(self)

    def __eq__(self, other):
        """Defaults to antisymmetry."""
        return self.__le__(other) and self.__ge__(other)

    def __or__(self, other):
        return self.join(other)

    def __and__(self, other):
        return self.meet(other)


class LatticeSpecialElement(Lattice):
    """A special element in a lattice, which could be bottom or top."""
    def __init__(self, *args, **kwargs):
        pass

    def _magic(self):
        raise NotImplementedError

    def __eq__(self, other):
        try:
            return self._magic() == other._magic()
        except AttributeError:
            return False

    def __repr__(self):
        return self.__class__.__name__


class FlatLattice(Lattice):
    """A flat lattice structure.

    For example, a flat domain of integers is the following::
                  ⊤
         ...  / / | \ \ ...
        ... -2 -1 0  1 2 ...
         ...  \ \ | / / ...
                  ⊥
    """
    def _superclass(self):
        try:
            return self.superclass
        except AttributeError:
            mro = [c for c in self.__class__.mro()
                   if c not in [Lattice, FlatLattice]]
            self.superclass = mro.pop(1)
            return self.superclass

    def join(self, other):
        if other == top(self.__class__):
            return other
        if other == bottom(self.__class__):
            return self
        if other != self:
            return top(self.__class__)
        return self

    def meet(self, other):
        if other == top(self.__class__):
            return self
        if other == bottom(self.__class__):
            return other
        if other != self:
            return bottom(self.__class__)
        return self

    def __le__(self, other):
        if self._superclass().__eq__(self, other):
            return True
        if other == top(self.__class__):
            return True
        return False

    def __repr__(self):
        return self.__class__.__name__ + \
            '(' + self._superclass().__repr__(self) + ')'


def top(cls):
    """Returns a top object of lattice class `cls`."""
    class Top(LatticeSpecialElement, cls):

        def _magic(self):
            return (cls, 'top')

        def join(self, other):
            return self

        def meet(self, other):
            return other

        def __le__(self, other):
            return self == other

    Top.__name__ = '_Top_' + cls.__name__
    return Top()


def bottom(cls):
    """Returns a bottom object of lattice class `cls`."""
    class Bottom(LatticeSpecialElement, cls):

        def _magic(self):
            return (cls, 'bottom')

        def join(self, other):
            return other

        def meet(self, other):
            return self

        def __le__(self, other):
            return True

    Bottom.__name__ = '_Bottom_' + cls.__name__
    return Bottom()


def flat(cls, name=None):
    """Returns a flat domain derived from a class `cls`, or a set of elements.
    """
    try:
        class Flattened(FlatLattice, cls):
            pass
    except TypeError:
        pass
    else:
        Flattened.__name__ = '_FlatLattice_' + cls.__name__
        return Flattened

    class _FlattenMe(object):
        def __init__(self, var):
            if not var in cls:
                raise ValueError('Non-existing element')
            self.v = var

        def __eq__(self, other):
            try:
                return self.v == other.v
            except AttributeError:
                return False

        def __repr__(self):
            return repr(self.v)

    if name:
        _FlattenMe.__name__ = name
    return flat(_FlattenMe)
