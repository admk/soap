"""
.. module:: soap.lattice.flat
    :synopsis: The flat lattice.
"""
from soap.lattice import Lattice
from soap.lattice.common import _is_class, _lattice_factory


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
        if self._class() is not None:
            self.v = self._class()(var)
        else:
            if self._container() is not None and var not in self._container():
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

    def __str__(self):
        s = super().__str__()
        if s is not None:
            return s
        return str(self.v)

    def __repr__(self):
        r = super().__repr__()
        if r is not None:
            return r
        return '%s(%s)' % (self.__class__.__name__, repr(self.v))


def flat(cls=None, name=None):
    """Returns a flat lattice derived from a class `cls`, or a set of elements.

    :param cls: The class to be lifted with a bottom element and crowned with a
        top element.
    :type cls: type
    :param name: The name of the generated class.
    :type name: str
    """
    if not name and _is_class(cls):
        name = 'FlatLattice_' + cls.__name__
    return _lattice_factory(cls, FlatLattice, name)


def denotational(cls=None, name=None):
    """Defines a classical denotational approach to flat domains.

    For example, for any mathematical operations, e.g., a + b, if either a or
    b is undefined (⊥), then the evaluation result is undefined. Because this
    behaviour is also given for comparisons including ``<=`` (less than or
    equal to), the original partial ordering from the lattice cannot be used
    anymore.

    Example::
        >>> Int = denotational(int, 'Int')
        >>> a, b, c = Int(1), Int(2), Int(bottom=True)
        >>> a + b
        Int(3)
        >>> a + c
        Int(bottom=True)
    """
    class Denotational(flat(cls)):
        def __str__(self):
            s = super().__str__()
            if s is not None:
                return s
            return str(self.v)

        def __repr__(self):
            r = super().__repr__()
            if r is not None:
                return r
            return self.__class__.__name__ + '(' + repr(self.v) + ')'

        def _op(self, op, other):
            try:
                if self.is_top() or other.is_top():
                    # top denotes conflict
                    return self.__class__(top=True)
            except AttributeError:
                pass
            try:
                if self.is_bottom() or other.is_bottom():
                    # bottom denotes no information
                    return self.__class__(bottom=True)
            except AttributeError:
                pass
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
    if name:
        Denotational.__name__ = name
    elif _is_class(cls):
        Denotational.__name__ += cls.__name__
    return Denotational
