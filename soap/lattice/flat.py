"""
.. module:: soap.lattice.flat
    :synopsis: The flat lattice.
"""
from soap.lattice.base import Lattice
from soap.lattice.common import _lattice_factory


class FlatLattice(Lattice):
    """A flat lattice structure.

    For example, a flat domain of integers is the following::
                  ⊤
         ...  / / | \ \ ...
        ... -2 -1 0  1 2 ...
         ...  \ \ | / / ...
                  ⊥
    """
    def __init__(self, value=None, top=False, bottom=False):
        super().__init__(top=top, bottom=bottom)
        if top or bottom:
            return
        self.v = self._cast_value(value)

    def _cast_value(self):
        raise NotImplementedError

    def is_top(self):
        return False

    def is_bottom(self):
        return False

    def join(self, other):
        if other != self:
            return self.__class__(top=True)
        return self

    def meet(self, other):
        if other != self:
            return self.__class__(bottom=True)
        return self

    def le(self, other):
        return self.v == other.v

    def __hash__(self):
        return hash((self.__class__, self.v))

    def __str__(self):
        return str(self.v)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.v)


class Denotational(object):
    def _op(self, op, other=None):
        try:
            if self.is_top() or (other is not None and other.is_top()):
                # top denotes conflict
                return self.__class__(top=True)
        except AttributeError:
            pass
        try:
            if self.is_bottom() or (other is not None and other.is_bottom()):
                # bottom denotes no information
                return self.__class__(bottom=True)
        except AttributeError:
            pass
        if other is None:
            v = op(self.v)
        else:
            try:
                v = op(self.v, other.v)
            except AttributeError:
                v = op(self.v, other)
        if type(v) is bool:
            return v
        return self.__class__(v)

    def __add__(self, other):
        return self._op(lambda x, y: x + y, other)
    __radd__ = __add__

    def __sub__(self, other):
        return self._op(lambda x, y: x - y, other)

    def __rsub__(self, other):
        return self._op(lambda x, y: y - x, other)

    def __mul__(self, other):
        return self._op(lambda x, y: x * y, other)
    __rmul__ = __mul__

    def __pos__(self):
        return self

    def __neg__(self):
        return self._op(lambda v: -v)

    def __abs__(self):
        return self._op(lambda v: abs(v))

    def __int__(self):
        return int(self.v)

    def __float__(self):
        return float(self.v)

    def __le__(self, other):
        return self._op(lambda x, y: x <= y, other)

    def __lt__(self, other):
        return self._op(lambda x, y: x < y, other)

    def __ge__(self, other):
        return self._op(lambda x, y: x >= y, other)

    def __gt__(self, other):
        return self._op(lambda x, y: x > y, other)

    def __ne__(self, other):
        return self._op(lambda x, y: x != y, other)

    def __eq__(self, other):
        return self._op(lambda x, y: x == y, other)


def flat(cls=None, name=None):
    """Returns a flat lattice derived from a class `cls`, or a set of elements.

    :param cls: The class to be lifted with a bottom element and crowned with a
        top element.
    :type cls: type
    :param name: The name of the generated class.
    :type name: str
    """
    if not name and callable(cls):
        name = 'FlatLattice_' + cls.__name__
    return _lattice_factory(cls, FlatLattice, name)


def denotational(cls=None, name=None):
    """Defines a classical denotational approach to flat domains.

    For example, for any mathematical operations, e.g., a + b, if either a
    or b is undefined (⊥), then the evaluation result is undefined. Because
    this behaviour is also given for comparisons including ``<=`` (less than
    or equal to), the original partial ordering from the lattice can only be
    accessed with the member function member:`le`.

    Example::
        >>> Int = denotational(int, 'Int')
        >>> a, b, c = Int(1), Int(2), Int(bottom=True)
        >>> a + b
        Int(3)
        >>> a + c
        Int(bottom=True)
    """
    class DenotationalFlatLattice(Denotational, flat(cls)):
        pass
    if name:
        DenotationalFlatLattice.__name__ = name
    elif callable(cls):
        DenotationalFlatLattice.__name__ += cls.__name__
    return DenotationalFlatLattice
