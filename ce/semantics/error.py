import itertools
import gmpy2
from gmpy2 import RoundUp, RoundDown, mpfr, mpq as _mpq

from ce.common import Comparable


mpfr_type = type(mpfr('1.0'))
mpq_type = type(_mpq('1.0'))


def mpq(v):
    if not isinstance(v, mpfr_type):
        return _mpq(v)
    try:
        m, e = v.as_mantissa_exp()
    except (OverflowError, ValueError):
        return v
    return _mpq(m, mpq(2) ** (-e))


def ulp(v):
    if type(v) is not mpfr_type:
        with gmpy2.local_context(round=gmpy2.RoundAwayZero):
            v = mpfr(v)
    try:
        return mpq(2) ** v.as_mantissa_exp()[1]
    except OverflowError:
        return mpfr('Inf')


def round_op(f):
    def wrapped(v1, v2, mode):
        with gmpy2.local_context(round=mode):
            return f(v1, v2)
    return wrapped


def round_off_error(interval):
    error = ulp(max(abs(interval.min), abs(interval.max))) / 2
    return FractionInterval([-error, error])


def round_off_error_from_exact(v):
    def round(exact):
        exact = mpq(exact)
        rounded = mpq(mpfr(exact))
        return rounded - exact
    with gmpy2.local_context(round=gmpy2.RoundDown):
        vr = round(v)
    with gmpy2.local_context(round=gmpy2.RoundUp):
        wr = round(v)
    return FractionInterval([vr, wr])


def cast_error_constant(v):
    return ErrorSemantics([v, v], round_off_error_from_exact(v))


def cast_error(v, w=None):
    w = w if w else v
    return ErrorSemantics(
        [v, w], round_off_error(FractionInterval([v, w])))


class Interval(object):

    def __init__(self, v):
        min_val, max_val = v
        self.min, self.max = min_val, max_val
        if min_val > max_val:
            raise ValueError('min_val cannot be greater than max_val')

    def __iter__(self):
        return iter((self.min, self.max))

    def __add__(self, other):
        return Interval([self.min + other.min, self.max + other.max])

    def __sub__(self, other):
        return Interval([self.min - other.max, self.max - other.min])

    def __mul__(self, other):
        v = (self.min * other.min, self.min * other.max,
             self.max * other.min, self.max * other.max)
        return Interval([min(v), max(v)])

    def __str__(self):
        return '[%s, %s]' % (str(self.min), str(self.max))

    def __eq__(self, other):
        if not isinstance(other, Interval):
            return False
        return self.min == other.min and self.max == other.max

    def __hash__(self):
        return hash(tuple(self))


class FloatInterval(Interval):

    def __init__(self, v):
        min_val, max_val = v
        with gmpy2.local_context(round=RoundDown):
            min_val = mpfr(min_val)
        with gmpy2.local_context(round=RoundUp):
            max_val = mpfr(max_val)
        super().__init__((min_val, max_val))

    def __add__(self, other):
        f = round_op(lambda x, y: x + y)
        return FloatInterval(
            [f(self.min, other.min, RoundDown),
             f(self.max, other.max, RoundUp)])

    def __sub__(self, other):
        f = round_op(lambda x, y: x - y)
        return FloatInterval(
            [f(self.min, other.max, RoundDown),
             f(self.max, other.min, RoundUp)])

    def __mul__(self, other):
        f = round_op(lambda x, y: x * y)
        l = itertools.product((self.min, self.max),
                              (other.min, other.max),
                              (RoundDown, RoundUp))
        v = [f(x, y, m) for x, y, m in l]
        return FloatInterval([min(v), max(v)])


class FractionInterval(Interval):

    def __init__(self, v):
        min_val, max_val = v
        super().__init__((mpq(min_val), mpq(max_val)))

    def __str__(self):
        return '[~%s, ~%s]' % (str(mpfr(self.min)), str(mpfr(self.max)))


class ErrorSemantics(Comparable):

    def __init__(self, v, e):
        self.v = FloatInterval(v)
        self.e = FractionInterval(e)

    def __add__(self, other):
        v = self.v + other.v
        e = self.e + other.e + round_off_error(v)
        return ErrorSemantics(v, e)

    def __sub__(self, other):
        v = self.v - other.v
        e = self.e - other.e + round_off_error(v)
        return ErrorSemantics(v, e)

    def __mul__(self, other):
        v = self.v * other.v
        e = self.e * other.e + round_off_error(v)
        e += FractionInterval(self.v) * other.e
        e += FractionInterval(other.v) * self.e
        return ErrorSemantics(v, e)

    def __str__(self):
        return '%sx%s' % (self.v, self.e)

    def __repr__(self):
        return 'ErrorSemantics([%s, %s], [%s, %s])' % \
            (repr(self.v.min), repr(self.v.max),
             repr(self.e.min), repr(self.e.max))

    def __eq__(self, other):
        if not isinstance(other, ErrorSemantics):
            return False
        return self.v == other.v and self.e == other.e

    def __lt__(self, other):
        def max_err(a):
            return max(abs(a.e.min), abs(a.e.max))
        return max_err(self) < max_err(other)

    def __hash__(self):
        return hash((self.v, self.e))


if __name__ == '__main__':
    gmpy2.set_context(gmpy2.ieee(32))
    print(FloatInterval(['0.1', '0.2']) * FloatInterval(['5.3', '6.7']))
    print(float(ulp(mpfr('0.1'))))
    mult = lambda x, y: x * y
    args = [mpfr('0.3'), mpfr('2.6')]
    print(round_op(mult)(*(args + [gmpy2.RoundDown])))
    print(round_op(mult)(*(args + [gmpy2.RoundUp])))
    a = FloatInterval(['0.3', '0.3'])
    print(a, round_off_error(a))
    x = cast_error('0.9', '1.1')
    for i in range(10):
        x *= x
        print(i, x)
