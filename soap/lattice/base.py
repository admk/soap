from functools import wraps

from soap.lattice.meta import LatticeMeta


def _decorate(cls):
    if not hasattr(cls, '_decorated'):
        cls._decorated = set()
    if cls is Lattice or cls in cls._decorated:
        return

    def check_return(func):
        @wraps(func)
        def checker(*args, **kwargs):
            v = func(*args, **kwargs)
            if v is not None:
                return v
            raise RuntimeError('Function {} does not return a value'.format(
                func.__qualname__))
        return checker

    def decorate_self(base_func, decd_func):
        if not decd_func:
            raise ValueError(
                'No function matching {} from class {} to decorate'.format(
                    base_func.__qualname__, cls))

        @check_return
        @wraps(decd_func)
        def wrapper(self):
            t = base_func(self)
            return t if t is not None else decd_func(self)

        return wrapper

    def decorate_self_other(base_func, decd_func):
        if not decd_func:
            raise ValueError('No matching {} function to decorate'.format(
                base_func.__qualname__))

        @check_return
        @wraps(decd_func)
        def wrapper(self, other):
            t = base_func(self, other)
            return t if t is not None else decd_func(self, other)

        return wrapper

    cls.__str__ = decorate_self(Lattice.__str__, cls.__str__)
    cls.__repr__ = decorate_self(Lattice.__repr__, cls.__repr__)
    cls.__hash__ = decorate_self(Lattice.__hash__, cls.__hash__)
    cls.is_top = decorate_self(Lattice.is_top, cls.is_top)
    cls.is_bottom = decorate_self(Lattice.is_bottom, cls.is_bottom)
    cls.join = decorate_self_other(Lattice.join, cls.join)
    cls.meet = decorate_self_other(Lattice.meet, cls.meet)
    cls.le = decorate_self_other(Lattice.le, cls.le)
    cls._decorated.add(cls)
    return cls


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
        if not isinstance(other, self.__class__):
            return False
        if self.is_bottom() or other.is_top():
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
