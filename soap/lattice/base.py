from functools import wraps

from soap.common.cache import Flyweight
from soap.lattice.meta import LatticeMeta


def _decorate(cls):
    if not hasattr(cls, '_decorated'):
        cls._decorated = set()
    if cls is Lattice or cls in cls._decorated:
        return

    def decorate_self(base_func, decd_func):
        if not decd_func:
            raise ValueError(
                'No function matching {} from class {} to decorate'.format(
                    base_func.__qualname__, cls))

        @wraps(decd_func)
        def wrapper(self):
            t = base_func(self)
            return t if t is not None else decd_func(self)

        return wrapper

    def decorate_self_other(base_func, decd_func):
        if not decd_func:
            raise ValueError('No matching {} function to decorate'.format(
                base_func.__qualname__))

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


def _compare(func):
    def wrapped_func(self, other):
        try:
            return func(self, other)
        except AttributeError:
            return False
    return wrapped_func


class Lattice(Flyweight, metaclass=LatticeMeta):
    """Common lattice structure.

    Because the partial orders we are using are always complete lattices,
    structures such as preorders, partial orders, dcpos are not implemented.

    Subclasses of this class must implement the member functions:
    :member:`join`, :member:`meet`, :member:`le`.
    """
    __slots__ = ('_hash')

    def __init__(self, *args, top=False, bottom=False, **kwargs):
        super().__init__()
        if top and bottom:
            raise ValueError(
                'Lattice element cannot be bottom and top simultaneously.')
        self.top = top
        self.bottom = bottom
        self._hash = None

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

    __le__ = _compare(lambda self, other: self.le(other))
    __lt__ = _compare(
        lambda self, other: self.le(other) and not other.le(self))
    __ge__ = _compare(lambda self, other: other.le(self))
    __gt__ = _compare(
        lambda self, other: other.le(self) and not self.le(other))
    __eq__ = _compare(lambda self, other: self.le(other) and other.le(self))
    __ne__ = _compare(
        lambda self, other: not self.le(other) or not other.le(self))

    def __hash__(self):
        hash_val = self._hash
        if hash_val:
            return hash_val
        is_top = self.is_top()
        is_bottom = self.is_bottom()
        if is_top or is_bottom:
            hash_val = hash((self.__class__, is_top, is_bottom))
            self._hash = hash_val
            return hash_val

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
