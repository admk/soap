"""
.. module:: soap.semantics.error
    :synopsis: Intervals and error semantics.
"""
import functools

import gmpy2
from gmpy2 import mpfr as _mpfr, mpq as _mpq, mpz

from soap import logger
from soap.common import ignored
from soap.lattice import Lattice


mpz_type = type(mpz('1'))
mpfr_type = type(_mpfr('1.0'))
mpq_type = type(_mpq('1.0'))
inf = _mpfr('Inf')


def _unpack(v):
    if type(v) is str:
        return v, v
    try:
        v_min, v_max = v
        return v_min, v_max
    except (ValueError, TypeError):  # cannot unpack
        return v, v


def _are_instance(v, t):
    return all(isinstance(e, t) for e in _unpack(v))


def mpfr(v):
    """Guards `gmpy2.mpfr` for a malformed string conversion segfault bug."""
    float(v)  # let it throw
    return _mpfr(v)


def mpq(v):
    """Unifies how mpq behaves when shit (overflow and NaN) happens.

    Also the conversion from mantissa exponent is necessary because the
    original mpq is not exact."""
    if not isinstance(v, mpfr_type):
        try:
            return _mpq(v)
        except ValueError:
            raise ValueError('Invalid value {}'.format(v))
    try:
        m, e = v.as_mantissa_exp()
    except (OverflowError, ValueError):
        return v
    return _mpq(m, mpq(2) ** (-e))


def ulp(v, underflow=True):
    """Computes the unit of the last place for a value.

    FIXME big question: what is ulp(0)?
    Definition: distance from 0 to its nearest floating-point value.

    Solutions::
      1. gradual underflow -> 2 ** (1 - offset - p)
          don't need to change definition, possibly, don't know how mpfr
          handles underflow stuff.
      2. abrupt underflow -> 2 ** (1 - offset)
          add 2 ** (1 - offset) overestimation to ulp.

    :param v: The value.
    :type v: any gmpy2 values
    """
    if underflow:
        underflow_error = mpq(2) ** gmpy2.get_context().emin
    else:
        underflow_error = 0
    if v == 0:  # corner case, exponent is 1
        return underflow_error
    if type(v) is not mpfr_type:
        with gmpy2.local_context(round=gmpy2.RoundAwayZero):
            v = mpfr(v)
    try:
        with gmpy2.local_context(round=gmpy2.RoundUp):
            return mpfr(mpq(2) ** v.as_mantissa_exp()[1] + underflow_error)
    except OverflowError:
        return mpfr('Inf')


def overapproximate_error(e):
    f = []
    e_min, e_max = _unpack(e)
    for v, r in [(e_min, gmpy2.RoundDown), (e_max, gmpy2.RoundUp)]:
        with gmpy2.local_context(round=r):
            f.append(mpfr(v))
    return FloatInterval(f)


def round_off_error(v):
    v_min, v_max = _unpack(v)
    error = ulp(max(abs(v_min), abs(v_max))) / 2
    return FloatInterval([-error, error])


def round_off_error_from_exact(v):
    e = mpq(v) - mpq(mpfr(v))
    return overapproximate_error([e, e])


def cast_error_constant(v):
    return ErrorSemantics([v, v], round_off_error_from_exact(v))


def cast_error(v, w=None):
    w = w if w else v
    if v == w:
        return cast_error_constant(v)
    return ErrorSemantics([v, w], round_off_error([v, w]))


def _coerce(self, other):
    if type(self) is type(other):
        return None
    dominance_poset = {
        (int, IntegerInterval): IntegerInterval,
        (int, FloatInterval): FloatInterval,
        (int, ErrorSemantics): ErrorSemantics,
        (mpz_type, IntegerInterval): IntegerInterval,
        (mpz_type, FloatInterval): FloatInterval,
        (mpz_type, ErrorSemantics): ErrorSemantics,
        (float, IntegerInterval): FloatInterval,
        (float, FloatInterval): FloatInterval,
        (float, ErrorSemantics): ErrorSemantics,
        (mpfr_type, IntegerInterval): FloatInterval,
        (mpfr_type, FloatInterval): FloatInterval,
        (mpfr_type, ErrorSemantics): ErrorSemantics,
        (IntegerInterval, FloatInterval): FloatInterval,
        (IntegerInterval, ErrorSemantics): ErrorSemantics,
        (FloatInterval, ErrorSemantics): ErrorSemantics,
    }
    try:
        return dominance_poset[self.__class__, other.__class__]
    except KeyError:
        pass
    try:
        return dominance_poset[other.__class__, self.__class__]
    except KeyError:
        raise TypeError(
            'Do not know how to coerce values {!r} and {!r} into the same '
            'type.'.format(self, other))


def _decorate_coerce(func):
    @functools.wraps(func)
    def wrapper(self, other):
        return func(self, other, _coerce(self, other))
    return wrapper


def _decorate_operator(func):
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
        try:
            return _decorate_coerce(func)(self, other)
        except gmpy2.RangeError:
            logger.warning('gmpy2 throws RangeError, default to top.')
            return self.__class__(top=True)
    return wrapper


class Interval(Lattice):
    """The interval base class."""
    def __init__(self, v=None, top=False, bottom=False):
        if isinstance(v, Interval):
            top = top or v.is_top()
            bottom = bottom or v.is_bottom()
        super().__init__(top=top, bottom=bottom)
        if top or bottom:
            return
        self.min, self.max = _unpack(v)
        if self.min > self.max:
            raise ValueError('min_val cannot be greater than max_val')

    def is_top(self):
        return self.min == float('-Inf') and self.max == float('Inf')

    def is_bottom(self):
        return False

    @property
    def min(self):
        try:
            return self._min
        except AttributeError:
            pass
        if self.is_top():
            return -inf
        if self.is_bottom():
            raise AttributeError('{!r} has no attribute "min"'.format(self))
        raise AttributeError(
            '{!r} is not top or bottom but has no attribute "min"'
            .format(self))

    @min.setter
    def min(self, v):
        self._min = v

    @property
    def max(self):
        try:
            return self._max
        except AttributeError:
            pass
        if self.is_top():
            return inf
        if self.is_bottom():
            raise AttributeError(
                'Bottom {!r} has no attribute "max"'.format(self))
        raise AttributeError(
            '{!r} is not top or bottom but has no attribute "max"'
            .format(self))

    @max.setter
    def max(self, v):
        self._max = v

    @_decorate_coerce
    def join(self, other, cls):
        if cls is not None:
            return cls(self) | cls(other)
        return self.__class__(
            [min(self.min, other.min), max(self.max, other.max)])

    @_decorate_coerce
    def meet(self, other, cls):
        if cls is not None:
            return cls(self) & cls(other)
        try:
            return self.__class__(
                [max(self.min, other.min), min(self.max, other.max)])
        except ValueError:  # min >= max
            return self.__class__(bottom=True)

    @_decorate_coerce
    def le(self, other, cls):
        if cls is not None:
            return cls(self).le(cls(other))
        return self.min >= other.min and self.max <= other.max

    def __iter__(self):
        return iter((self.min, self.max))

    def __contains__(self, v):
        return self.min <= v <= self.max

    def __getitem__(self, key):
        try:
            k_min, k_max = key
        except (TypeError, ValueError):
            raise KeyError('Do not know how to produce the error interval '
                           'from {}'.format(key))
        return ErrorSemantics(self, [k_min, k_max])

    @_decorate_operator
    def __add__(self, other, cls):
        if cls is not None:
            return cls(self) + cls(other)
        return self.__class__([self.min + other.min, self.max + other.max])
    __radd__ = __add__

    @_decorate_operator
    def __sub__(self, other, cls):
        if cls is not None:
            return cls(self) - cls(other)
        return self.__class__([self.min - other.max, self.max - other.min])

    @_decorate_operator
    def __rsub__(self, other, cls):
        if cls is not None:
            return cls(other) - cls(self)
        return other - self

    @_decorate_operator
    def __mul__(self, other, cls):
        if cls is not None:
            return cls(self) * cls(other)
        v = (self.min * other.min, self.min * other.max,
             self.max * other.min, self.max * other.max)
        return self.__class__([min(v), max(v)])
    __rmul__ = __mul__

    @_decorate_operator
    def __truediv__(self, other, cls):
        if cls is not None:
            return cls(self) / cls(other)
        if 0 not in other:
            v = (self.min / other.min, self.min / other.max,
                 self.max / other.min, self.max / other.max)
        else:
            logger.warning(
                '{} / {} has potential zero division error.'
                .format(self, other))
            if other <= self.__class__([-inf, 0]):
                v = (self.min * -inf, self.min / other.min,
                     self.max * -inf, self.max / other.min)
            elif other <= self.__class__([0, inf]):
                v = (self.min / other.max, self.min * inf,
                     self.max / other.max, self.max * inf)
            else:
                v = (-inf, inf)
        return self.__class__([min(v), max(v)])

    @_decorate_operator
    def __rtruediv__(self, other, cls):
        if cls is not None:
            return cls(other) / cls(self)
        return other / self

    def __neg__(self):
        if self.is_top() or self.is_bottom():
            return self
        return self.__class__([-self.max, -self.min])

    @_decorate_operator
    def widen(self, other, cls):
        if cls is not None:
            return cls(self).widen(cls(other))
        min_val = -inf if other.min < self.min else self.min
        max_val = inf if other.max > self.max else self.max
        return self.__class__([min_val, max_val])

    def __str__(self):
        min_val = '-∞' if self.min == -inf else self.min
        max_val = '∞' if self.max == inf else self.max
        if min_val == max_val:
            return str(min_val)
        return '[{}, {}]'.format(min_val, max_val)

    def __repr__(self):
        return '{cls}([{min!r}, {max!r}])'.format(
            cls=self.__class__.__name__, min=self.min, max=self.max)

    def __hash__(self):
        return hash(tuple(self))


class IntegerInterval(Interval):
    """The interval containing integer values."""
    def __init__(self, v=None, top=False, bottom=False):
        super().__init__(v, top=top, bottom=bottom)
        try:
            if self.min not in (-inf, inf):
                self.min = mpz(self.min)
            if self.max not in (-inf, inf):
                self.max = mpz(self.max)
        except AttributeError:
            'The interval is a top or bottom.'


class FloatInterval(Interval):
    """The interval containing floating point values."""
    def __init__(self, v=None, top=False, bottom=False):
        super().__init__(v, top=top, bottom=bottom)
        if top or bottom:
            return
        try:
            self.min = mpfr(self.min)
            self.max = mpfr(self.max)
        except AttributeError:
            'The interval is a top or bottom.'

    def __str__(self):
        min_val = '-∞' if self.min == -inf else '{:.5g}'.format(self.min)
        max_val = '∞' if self.max == inf else '{:.5g}'.format(self.max)
        return '[{}, {}]'.format(min_val, max_val)


class FractionInterval(Interval):
    """The interval containing real rational values."""
    def __init__(self, v=None, top=False, bottom=False):
        super().__init__(v, top=top, bottom=bottom)
        if top or bottom:
            return
        self.min = mpq(self.min)
        self.max = mpq(self.max)

    def __str__(self):
        min_val = '-∞' if self.min == -inf else '{:.5g}'.format(self.min)
        max_val = '∞' if self.max == inf else '{:.5g}'.format(self.max)
        return '[{}, {}]'.format(min_val, max_val)


class ErrorSemantics(Lattice):
    """The error semantics."""
    def __init__(self, v=None, e=None, top=False, bottom=False):
        super().__init__(top=top, bottom=bottom)
        if top or bottom:
            return

        def error(v, e):
            if isinstance(e, FloatInterval):
                return e
            if e is not None:
                return overapproximate_error(e)
            v_min, v_max = _unpack(v)
            if _are_instance(v, (int, mpz_type)):
                abs_val = max(abs(v_min), abs(v_max))
                if mpfr(abs_val) == abs_val:
                    # some integers cannot be expressed exactly in fp values
                    return FloatInterval(0)
            if v_min == v_max:
                return round_off_error_from_exact(v_min)
            return round_off_error(FloatInterval(v))

        if isinstance(v, ErrorSemantics):
            self.v, self.e = v
        else:
            self.v, self.e = FloatInterval(v), error(v, e)

    def is_top(self):
        return self.v.is_top()

    def is_bottom(self):
        return self.v.is_bottom()

    @_decorate_coerce
    def join(self, other, cls):
        if cls is not None:
            return cls(self) | cls(other)
        return self.__class__(self.v | other.v, self.e | other.e)

    @_decorate_coerce
    def meet(self, other, cls):
        if cls is not None:
            return cls(self) & cls(other)
        return self.__class__(self.v & other.v, self.e & other.e)

    @_decorate_coerce
    def le(self, other, cls):
        if cls is not None:
            return cls(self).le(cls(other))
        return self.v.le(other.v) and self.e.le(other.e)

    def __iter__(self):
        return iter((self.v, self.e))

    def __contains__(self, v):
        return self.v.min <= v <= self.v.max

    @_decorate_operator
    def __add__(self, other, cls):
        if cls is not None:
            return cls(self) + cls(other)
        v = self.v + other.v
        e = self.e + other.e + round_off_error(v)
        return self.__class__(v, e)
    __radd__ = __add__

    @_decorate_operator
    def __sub__(self, other, cls):
        if cls is not None:
            return cls(self) - cls(other)
        v = self.v - other.v
        e = self.e - other.e + round_off_error(v)
        return self.__class__(v, e)

    @_decorate_operator
    def __rsub__(self, other, cls):
        if cls is not None:
            return cls(other) - cls(self)
        return other - self

    @_decorate_operator
    def __mul__(self, other, cls):
        if cls is not None:
            return cls(self) * cls(other)
        v = self.v * other.v
        e = self.e * other.e + round_off_error(v)
        e += self.v * other.e
        e += other.v * self.e
        return self.__class__(v, e)
    __rmul__ = __mul__

    @_decorate_operator
    def __truediv__(self, other, cls):
        if cls is not None:
            return cls(self) / cls(other)
        v = self.v / other.v
        e = self.e - v * other.e
        e /= other.v + other.e
        return self.__class__(v, e)

    @_decorate_operator
    def __rtruediv__(self, other, cls):
        if cls is not None:
            return cls(other) / cls(self)
        return other / self

    def __neg__(self):
        if self.is_top() or self.is_bottom():
            return self
        return self.__class__(-self.v, -self.e)

    @_decorate_operator
    def widen(self, other, cls):
        if cls is not None:
            return cls(self).widen(cls(other))
        return self.__class__(self.v.widen(other.v), self.e | other.e)

    def __abs__(self):
        return self.v + self.e

    def __getitem__(self, key):
        try:
            k_min, k_max = key
        except (TypeError, ValueError):
            raise KeyError(
                'Do not know how to produce the error interval from {}'
                .format(key))
        return ErrorSemantics(self.v, [k_min, k_max])

    def __str__(self):
        return '{value}{error}'.format(value=self.v, error=self.e)

    def __repr__(self):
        return '{cls}({value!}, {error!r})'.format(
            cls=self.__class__.__name__, value=self.v, error=self.e)

    def __hash__(self):
        return hash((self.v, self.e))


def cast(v=None):
    if v is None:
        return IntegerInterval(bottom=True)
    if isinstance(v, str):
        if v.isdigit():
            return IntegerInterval(v)
        return ErrorSemantics(v)
    if isinstance(v, (Interval, ErrorSemantics)):
        return v
    try:
        v_min, v_max = v
    except (ValueError, TypeError):
        if isinstance(v, (int, mpz_type)):
            return IntegerInterval(v)
        if isinstance(v, (float, mpfr_type)):
            return ErrorSemantics(v)
    else:
        if _are_instance((v_min, v_max), str):
            if v_min.isdigit() and v_max.isdigit():
                return IntegerInterval(v)
            return ErrorSemantics(v)
        if _are_instance((v_min, v_max), (int, mpz_type)):
            return IntegerInterval(v)
        isfloat = lambda val: isinstance(val, (float, mpfr_type))
        if isfloat(v_min) or isfloat(v_max):
            return ErrorSemantics(v)
    raise TypeError('Do not know how to cast value {!r}'.format(v))
