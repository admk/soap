import copy
from functools import wraps


class LatticeMeta(type):
    """The metaclass of lattices.

    It defines the behaviour of the systematic design of lattices."""
    def __add__(self_class, other_class):
        class UnifiedSummationLattice(Lattice):
            """Defines a summation of two partial orders with unified top and
            bottom elements."""
            def __init__(self, *args, top=False, bottom=False, **kwargs):
                super().__init__(top=top, bottom=bottom)
                if top or bottom:
                    return
                for c in (self_class, other_class):
                    v = self._try_class(c, *args, **kwargs)
                    if v is not NotImplemented:
                        break
                self.v = v

            def _try_class(self, cls, *args, **kwargs):
                if len(args) == 1:
                    if isinstance(args[0], cls):
                        return cls
                try:
                    return cls(*args, **kwargs)
                except Exception:
                    return NotImplemented

            def is_top(self):
                return self.v.is_top()

            def is_bottom(self):
                return self.v.is_bottom()

            def join(self, other):
                if type(self.v) is not type(other.v):
                    return self.__class__(top=True)
                return self.v | other.v

            def meet(self, other):
                if type(self.v) is not type(other.v):
                    return self.__class__(bottom=True)
                return self.v & other.v

            def le(self, other):
                if type(self.v) is not type(other.v):
                    return False
                return self.v <= other.v

            def __str__(self):
                return str(self.v)

            def __repr__(self):
                return '%s(%r)' % (self.__class__.__name__, self.v)

    def __mul__(self_class, other_class):
        class ComponentWiseLattice(Lattice):
            """Defines a component-wise partial order."""
            def __init__(self, self_obj=None, other_obj=None,
                         top=False, bottom=False):
                super().__init__(top=top, bottom=bottom)
                if top or bottom:
                    self.components = tuple(
                        cls(top=top, bottom=bottom)
                        for cls in (self_class, other_class))
                else:
                    self.components = (self_obj, other_obj)

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
                return '(%s)' % ', '.join(str(c) for c in self.components)

            def __repr__(self):
                return '%s(%s)' % \
                    (self.__class__.__name__,
                     ', '.join(repr(c) for c in self.components))

        ComponentWiseLattice.__name__ = 'ComponentWiseLattice_%s_%s' % \
            (self_class.__name__, other_class.__name__)
        return ComponentWiseLattice


def _decorate(cls):
    def _check_return(func):
        @wraps(func)
        def checker(*args, **kwargs):
            v = func(*args, **kwargs)
            if v is not None:
                return v
            raise RuntimeError('Function {} does not return a value'
                               ''.format(func.__qualname__))
        return checker

    def decorate_self(base_func, decd_func):
        @_check_return
        @wraps(decd_func)
        def wrapper(self):
            t = base_func(self)
            return t if t is not None else decd_func(self)
        return wrapper

    def decorate_self_other(base_func, decd_func):
        @_check_return
        @wraps(decd_func)
        def wrapper(self, other):
            t = base_func(self, other)
            return t if t is not None else decd_func(self, other)
        return wrapper
    try:
        if cls == Lattice or cls._decorated:
            return
    except AttributeError:
        cls._decorated = True
    cls.__str__ = decorate_self(Lattice.__str__, cls.__str__)
    cls.__repr__ = decorate_self(Lattice.__repr__, cls.__repr__)
    cls.__hash__ = decorate_self(Lattice.__hash__, cls.__hash__)
    cls.is_top = decorate_self(Lattice.is_top, cls.is_top)
    cls.is_bottom = decorate_self(Lattice.is_bottom, cls.is_bottom)
    cls.join = decorate_self_other(Lattice.join, cls.join)
    cls.meet = decorate_self_other(Lattice.meet, cls.meet)
    cls.le = decorate_self_other(Lattice.le, cls.le)


class Lattice(object, metaclass=LatticeMeta):
    """Common lattice structure.

    Because the partial orders we are using are always complete lattices,
    structures such as preorders, partial orders, dcpos are not implemented.

    Subclasses of this class must implement the member functions:
    :member:`join`, :member:`meet`, :member:`le`.
    """
    def __init__(self, *args, top=False, bottom=False, **kwargs):
        super().__init__()
        if top and bottom:
            raise ValueError(
                'Lattice element cannot be bottom and top simultaneously.')
        self.top = top
        self.bottom = bottom

        _decorate(self.__class__)

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

    def join(self, other):
        if self.is_top() or other.is_bottom():
            return self
        if self.is_bottom() or other.is_top():
            return other

    def meet(self, other):
        if self.is_top() or other.is_bottom():
            return other
        if self.is_bottom() or other.is_top():
            return self

    def le(self, other):
        if self.is_bottom():
            return True
        if other.is_top():
            return True
        if self.is_top() and not other.is_top():
            return False
        if not self.is_bottom() and other.is_bottom():
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

    def __hash__(self):
        if self.is_top() or self.is_bottom():
            return hash((self.__class__, self.is_top(), self.is_bottom()))

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
