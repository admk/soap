#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


import gmpy2
from gmpy2 import mpfr, mpq as _mpq


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
    from core import FractionInterval
    error = ulp(max(abs(interval.min), abs(interval.max))) / 2
    return FractionInterval([-error, error])


def round_off_error_from_exact(v):
    def round(exact):
        exact = mpq(exact)
        rounded = mpq(mpfr(exact))
        return rounded - exact
    from core import FractionInterval
    with gmpy2.local_context(round=gmpy2.RoundDown):
        vr = round(v)
    with gmpy2.local_context(round=gmpy2.RoundUp):
        wr = round(v)
    return FractionInterval([vr, wr])


def cast_error_constant(v):
    from core import ErrorSemantics
    return ErrorSemantics([v, v], round_off_error_from_exact(v))


def cast_error(v, w=None):
    from core import FractionInterval, ErrorSemantics
    w = w if w else v
    return ErrorSemantics(
        [v, w], round_off_error(FractionInterval([v, w])))


if __name__ == '__main__':
    from core import FloatInterval
    gmpy2.set_context(gmpy2.ieee(32))
    print float(ulp(mpfr('0.1')))
    mult = lambda x, y: x * y
    args = [mpfr('0.3'), mpfr('2.6')]
    print round_op(mult)(*(args + [gmpy2.RoundDown]))
    print round_op(mult)(*(args + [gmpy2.RoundUp]))
    a = FloatInterval(['0.3', '0.3'])
    print a, round_off_error(a)
    x = cast_error('0.9', '1.1')
    for i in xrange(10):
        x *= x
        print i, x
