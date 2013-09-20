"""
.. module:: soap.semantics.error
    :synopsis: Intervals and error semantics.
"""
import gmpy2
from gmpy2 import mpfr, mpq as _mpq

from soap.common import ignored
from soap.lattice import Lattice


mpfr_type = type(mpfr('1.0'))
mpq_type = type(_mpq('1.0'))


def mpq(v):
    """Unifies how mpq behaves when shit (overflow and NaN) happens.

    Also the conversion from mantissa exponent is necessary because the
    original mpq is not exact."""
    if not isinstance(v, mpfr_type):
        try:
            return _mpq(v)
        except ValueError:
            raise ValueError('Invalid value %s' % v)
    try:
        m, e = v.as_mantissa_exp()
    except (OverflowError, ValueError):
        return v
    return _mpq(m, mpq(2) ** (-e))


def ulp(v):
    """Computes the unit of the last place for a value.

    :param v: The value.
    :type v: any gmpy2 values
    """
    if type(v) is not mpfr_type:
        with gmpy2.local_context(round=gmpy2.RoundAwayZero):
            v = mpfr(v)
    try:
        return mpq(2) ** v.as_mantissa_exp()[1]
    except OverflowError:
        return mpfr('Inf')


def round_off_error(interval):
    error = ulp(max(abs(interval.min), abs(interval.max))) / 2
    return FractionInterval([-error, error])


def round_off_error_from_exact(v):
    e = mpq(v) - mpq(mpfr(v))
    return FractionInterval([e, e])


def cast_error_constant(v):
    return ErrorSemantics([v, v], round_off_error_from_exact(v))


def cast_error(v, w=None):
    w = w if w else v
    if v == w:
        return cast_error_constant(v)
    return ErrorSemantics([v, w], round_off_error(FractionInterval([v, w])))


def _decorate_cast_other(func):
    def wrapper(self, other):
        with ignored(AttributeError):
            if self.is_top() or other.is_top():
                # top denotes no information or non-termination
                return self.__class__(top=True)
        with ignored(AttributeError):
            if self.is_bottom() or other.is_bottom():
                # bottom denotes conflict
                return self.__class__(bottom=True)
        try:
            return func(self, other)
        except AttributeError:
            return func(self, self.__class__(other))
    return wrapper


class Interval(Lattice):
    """The interval base class."""
    def __init__(self, v=None, top=False, bottom=False):
        super().__init__(top=top, bottom=bottom)
        if top or bottom:
            return
        try:
            if type(v) is str:
                raise TypeError('_String')
            self.min, self.max = v
        except (ValueError, TypeError):
            self.min = self.max = v
        if self.min > self.max:
            raise ValueError('min_val cannot be greater than max_val')

    def is_top(self):
        t = super().is_top()
        if t is not None:
            return t
        return self.min == float('-Inf') and self.max == float('Inf')

    def is_bottom(self):
        b = super().is_bottom()
        return b if b is not None else False

    def join(self, other):
        e = super().join(other)
        if e:
            return e
        return self.__class__(
            [min(self.min, other.min), max(self.max, other.max)])

    def meet(self, other):
        e = super().meet(other)
        if e:
            return e
        return self.__class__(
            [max(self.min, other.min), min(self.max, other.max)])

    def le(self, other):
        le = super().le(other)
        if le is not None:
            return le
        return self.min >= other.min and self.max <= other.max

    def __iter__(self):
        return iter((self.min, self.max))

    @_decorate_cast_other
    def __add__(self, other):
        return self.__class__([self.min + other.min, self.max + other.max])
    __radd__ = __add__

    @_decorate_cast_other
    def __sub__(self, other):
        return self.__class__([self.min - other.max, self.max - other.min])

    @_decorate_cast_other
    def __rsub__(self, other):
        return self.__class__([other.min - self.max, other.max - self.min])

    @_decorate_cast_other
    def __mul__(self, other):
        v = (self.min * other.min, self.min * other.max,
             self.max * other.min, self.max * other.max)
        return self.__class__([min(v), max(v)])
    __rmul__ = __mul__

    def __neg__(self):
        if self.is_top() or self.is_bottom():
            return self
        return self.__class__([-self.max, -self.min])

    def __str__(self):
        s = super().__str__()
        if s is not None:
            return s
        return '[%s, %s]' % (str(self.min), str(self.max))

    def __hash__(self):
        return hash(tuple(self))


class FloatInterval(Interval):
    """The interval containing floating point values."""
    def __init__(self, v=None, top=False, bottom=False):
        super().__init__(v, top=top, bottom=bottom)
        self.min = mpfr(self.min)
        self.max = mpfr(self.max)


class FractionInterval(Interval):
    """The interval containing real rational values."""
    def __init__(self, v=None, top=False, bottom=False):
        super().__init__(v, top=top, bottom=bottom)
        self.min = mpq(self.min)
        self.max = mpq(self.max)

    def __str__(self):
        s = super(Lattice, self).__str__()
        if s is not None:
            return s
        return '[~%s, ~%s]' % (str(mpfr(self.min)), str(mpfr(self.max)))


class ErrorSemantics(Lattice):
    """The error semantics."""
    def __init__(self, v=None, e=None, top=False, bottom=False):
        super().__init__(top=top, bottom=bottom)
        if top or bottom:
            return
        self.v = FloatInterval(v)
        if e is not None:
            self.e = FractionInterval(e)
        elif self.v.min == self.v.max:
            self.e = round_off_error_from_exact(self.v.min)
        else:
            self.e = round_off_error(self.v)

    def is_top(self):
        t = super().is_top()
        return t if t is not None else self.v.is_top() or self.e.is_top()

    def is_bottom(self):
        b = super().is_bottom()
        return b if b is not None else self.v.is_bottom() or self.e.is_bottom()

    def join(self, other):
        e = super().join(other)
        if e:
            return e
        return self.__class__(self.v | other.v, self.e | other.e)

    def meet(self, other):
        e = super().meet(other)
        if e:
            return e
        return self.__class__(self.v & other.v, self.e & other.e)

    def le(self, other):
        le = super().le(other)
        if le is not None:
            return le
        return self.v.le(other.v) and self.e.le(other.e)

    @_decorate_cast_other
    def __add__(self, other):
        v = self.v + other.v
        e = self.e + other.e + round_off_error(v)
        return self.__class__(v, e)
    __radd__ = __add__

    @_decorate_cast_other
    def __sub__(self, other):
        v = self.v - other.v
        e = self.e - other.e + round_off_error(v)
        return self.__class__(v, e)

    @_decorate_cast_other
    def __rsub__(self, other):
        v = other.v - self.v
        e = other.e - self.e + round_off_error(v)
        return self.__class__(v, e)

    @_decorate_cast_other
    def __mul__(self, other):
        v = self.v * other.v
        e = self.e * other.e + round_off_error(v)
        e += FractionInterval(self.v) * other.e
        e += FractionInterval(other.v) * self.e
        return self.__class__(v, e)
    __rmul__ = __mul__

    def __neg__(self):
        if self.is_top() or self.is_bottom():
            return self
        return self.__class__(-self.v, -self.e)

    def __abs__(self):
        return self.v + self.e

    def __str__(self):
        s = super().__str__()
        if s is not None:
            return s
        return '%sx%s' % (self.v, self.e)

    def __repr__(self):
        r = super().__repr__()
        if r is not None:
            return r
        return '%s([%r, %r], [%r, %r])' % \
            (self.__class__.__name__,
             self.v.min, self.v.max, self.e.min, self.e.max)

    def __hash__(self):
        return hash((self.v, self.e))


if __name__ == '__main__':
    from soap.semantics import precision_context
    with precision_context(52):
        x = cast_error('0.1', '0.2')
        print(x)
        print(x * x)
    with precision_context(23):
        a = cast_error('5', '10')
        b = cast_error('0', '0.001')
        print((a + b) * (a + b))
    gmpy2.set_context(gmpy2.ieee(64))
    print(FloatInterval(['0.1', '0.2']) * FloatInterval(['5.3', '6.7']))
    print(float(ulp(mpfr('0.1'))))
    mult = lambda x, y: x * y
    args = [mpfr('0.3'), mpfr('2.6')]
    a = FloatInterval(['0.3', '0.3'])
    print(a, round_off_error(a))
    x = cast_error('0.9', '1.1')
    for i in range(20):
        x *= x
        print(i, x)
