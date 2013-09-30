"""
.. module:: soap.semantics.error
    :synopsis: Intervals and error semantics.
"""
import functools

import gmpy2
from gmpy2 import mpfr, mpq as _mpq

from soap.common import ignored
from soap.lattice import Lattice


mpfr_type = type(mpfr('1.0'))
mpq_type = type(_mpq('1.0'))

inf = mpfr('Inf')


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


def _coerce(self, other, use_self_func=False):
    if type(self) is type(other):
        return self, other

    def precedence(v):
        precedence_list = [
            ErrorSemantics, FloatInterval, FractionInterval, IntegerInterval
        ]
        try:
            return precedence_list.index(type(v))
        except ValueError:
            return len(precedence_list) + 1

    self_prec = precedence(self)
    other_prec = precedence(other)
    if self_prec > other_prec:
        if use_self_func:
            raise NotImplementedError
        return other.__class__(self), other
    return self, self.__class__(other)


def _decorate_coerce(func):
    @functools.wraps(func)
    def wrapper(self, other):
        try:
            self, other = _coerce(self, other, True)
        except NotImplementedError:
            return NotImplemented
        return func(self, other)
    return wrapper


def _decorate_default(func):
    @functools.wraps(func)
    def wrapper(self, other):
        with ignored(AttributeError):
            if self.is_top() or other.is_top():
                # top denotes no information or non-termination
                return self.__class__(top=True)
        with ignored(AttributeError):
            if self.is_bottom() or other.is_bottom():
                # bottom denotes conflict
                return self.__class__(bottom=True)
        return func(self, other)
    return wrapper


_decorate_operator = lambda func: _decorate_coerce(_decorate_default(func))


class Interval(Lattice):
    """The interval base class."""
    def __init__(self, v=None, top=False, bottom=False):
        if isinstance(v, Interval):
            top = top or v.is_top()
            bottom = bottom or v.is_bottom()
        super().__init__(top=top, bottom=bottom)
        if top or bottom:
            return
        if type(v) is str:
            self.min = self.max = v
        else:
            try:
                self.min, self.max = v
            except (ValueError, TypeError):  # cannot unpack
                self.min = self.max = v
        if self.min > self.max:
            raise ValueError('min_val cannot be greater than max_val')

    def is_top(self):
        return self.min == float('-Inf') and self.max == float('Inf')

    def is_bottom(self):
        return False

    @_decorate_coerce
    def join(self, other):
        return self.__class__(
            [min(self.min, other.min), max(self.max, other.max)])

    @_decorate_coerce
    def meet(self, other):
        try:
            return self.__class__(
                [max(self.min, other.min), min(self.max, other.max)])
        except ValueError:  # min >= max
            return self.__class__(bottom=True)

    def le(self, other):
        if type(self) is not type(other):
            self, other = _coerce(self, other)
            return self.le(other)
        return self.min >= other.min and self.max <= other.max

    def __iter__(self):
        return iter((self.min, self.max))

    def __contains__(self, v):
        return self.min <= v <= self.max

    @_decorate_operator
    def __add__(self, other):
        return self.__class__([self.min + other.min, self.max + other.max])
    __radd__ = __add__

    @_decorate_operator
    def __sub__(self, other):
        return self.__class__([self.min - other.max, self.max - other.min])

    @_decorate_operator
    def __rsub__(self, other):
        return other - self

    @_decorate_operator
    def __mul__(self, other):
        v = (self.min * other.min, self.min * other.max,
             self.max * other.min, self.max * other.max)
        return self.__class__([min(v), max(v)])
    __rmul__ = __mul__

    @_decorate_operator
    def __truediv__(self, other):
        if 0 not in other:
            v = (self.min / other.min, self.min / other.max,
                 self.max / other.min, self.max / other.max)
        elif other <= self.__class__([-inf, 0]):
            v = (self.min * -inf, self.min / other.min,
                 self.max * -inf, self.max / other.min)
        elif other <= self.__class__([0, inf]):
            v = (self.min / other.max, self.min * inf,
                 self.max / other.max, self.max * inf)
        else:
            v = (-inf, inf)
        return self.__class__([min(v), max(v)])

    @_decorate_operator
    def __rtruediv__(self, other):
        return other / self

    def __neg__(self):
        if self.is_top() or self.is_bottom():
            return self
        return self.__class__([-self.max, -self.min])

    def __str__(self):
        min_val = '-∞' if self.min == -inf else self.min
        max_val = '∞' if self.max == -inf else self.max
        return '[%s, %s]' % (min_val, max_val)

    def __repr__(self):
        return '%s([%r, %r])' % (self.__class__.__name__, self.min, self.max)

    def __hash__(self):
        return hash(tuple(self))


class IntegerInterval(Interval):
    """The interval containing integer values."""
    def __init__(self, v=None, top=False, bottom=False):
        super().__init__(v, top=top, bottom=bottom)
        try:
            if self.min not in (-inf, inf):
                self.min = int(self.min)
            if self.max not in (-inf, inf):
                self.max = int(self.max)
        except AttributeError:
            'The interval is a top or bottom.'


class FloatInterval(Interval):
    """The interval containing floating point values."""
    def __init__(self, v=None, top=False, bottom=False):
        super().__init__(v, top=top, bottom=bottom)
        try:
            self.min = mpfr(self.min)
            self.max = mpfr(self.max)
        except AttributeError:
            'The interval is a top or bottom.'

    def __str__(self):
        min_val = '-∞' if self.min == -inf else '%1.5g' % self.min
        max_val = '∞' if self.max == -inf else '%1.5g' % self.min
        return '~[%s, %s]' % (min_val, max_val)


class FractionInterval(Interval):
    """The interval containing real rational values."""
    def __init__(self, v=None, top=False, bottom=False):
        super().__init__(v, top=top, bottom=bottom)
        try:
            self.min = mpq(self.min)
            self.max = mpq(self.max)
        except AttributeError:
            'The interval is a top or bottom.'

    def __str__(self):
        min_val = '-∞' if self.min == -inf else '%1.5g' % self.min
        max_val = '∞' if self.max == -inf else '%1.5g' % self.min
        return '~[%s, %s]' % (min_val, max_val)


class ErrorSemantics(Lattice):
    """The error semantics."""
    def __init__(self, v=None, e=None, top=False, bottom=False):
        super().__init__(top=top, bottom=bottom)
        if top or bottom:
            return
        self.v = FloatInterval(v)

        def error(v):
            if e is not None:
                return FractionInterval(e)
            v_min, v_max = Interval(v)
            if isinstance(v_min, int) and isinstance(v_max, int):
                # FIXME some integers cannot be expressed exactly in fp values
                return FractionInterval(0)
            if v_min == v_max:
                return round_off_error_from_exact(v_min)
            return round_off_error(FloatInterval(v))

        self.e = error(v)

    def is_top(self):
        return self.v.is_top() or self.e.is_top()

    def is_bottom(self):
        return self.v.is_bottom() or self.e.is_bottom()

    @_decorate_coerce
    def join(self, other):
        return self.__class__(self.v | other.v, self.e | other.e)

    @_decorate_coerce
    def meet(self, other):
        return self.__class__(self.v & other.v, self.e & other.e)

    def le(self, other):
        if type(self) is not type(other):
            self, other = _coerce(self, other)
            return self.le(other)
        return self.v.le(other.v) and self.e.le(other.e)

    def __contains__(self, v):
        return self.v.min <= v <= self.v.max

    @_decorate_operator
    def __add__(self, other):
        v = self.v + other.v
        e = self.e + other.e + round_off_error(v)
        return self.__class__(v, e)
    __radd__ = __add__

    @_decorate_operator
    def __sub__(self, other):
        v = self.v - other.v
        e = self.e - other.e + round_off_error(v)
        return self.__class__(v, e)

    @_decorate_operator
    def __rsub__(self, other):
        return other - self

    @_decorate_operator
    def __mul__(self, other):
        v = self.v * other.v
        e = self.e * other.e + round_off_error(v)
        e += FractionInterval(self.v) * other.e
        e += FractionInterval(other.v) * self.e
        return self.__class__(v, e)
    __rmul__ = __mul__

    @_decorate_operator
    def __truediv__(self, other):
        v = self.v / other.v
        e = self.e - FractionInterval(v) * other.e
        e /= FractionInterval(other.v) + other.e
        return self.__class__(v, e)

    @_decorate_operator
    def __rtruediv__(self, other):
        return other / self

    def __neg__(self):
        if self.is_top() or self.is_bottom():
            return self
        return self.__class__(-self.v, -self.e)

    def __abs__(self):
        return FractionInterval(self.v) + self.e

    def __str__(self):
        return '(%s, %s)' % (self.v, self.e)

    def __repr__(self):
        return '%s([%r, %r], [%r, %r])' % \
            (self.__class__.__name__,
             self.v.min, self.v.max, self.e.min, self.e.max)

    def __hash__(self):
        return hash((self.v, self.e))
