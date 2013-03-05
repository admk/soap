#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


import gmpy2
from gmpy2 import mpq, mpfr


mpfr_type = type(mpfr('1.0'))
mpq_type = type(mpq('1.0'))


def ulp(v):
    if type(v) is not mpfr_type:
        with gmpy2.local_context(round=gmpy2.RoundAwayZero):
            v = mpfr(v)
    return mpq(2) ** v.as_mantissa_exp()[1]


def round_op(f):
    def wrapped(v1, v2, mode):
        with gmpy2.local_context(round=mode):
            return f(v1, v2)
    return wrapped


if __name__ == '__main__':
    gmpy2.set_context(gmpy2.ieee(32))
    print float(ulp(mpfr('0.1')))
    mult = lambda x, y: x * y
    args = [mpfr('0.3'), mpfr('2.6')]
    print round_op(mult)(*(args + [gmpy2.RoundDown]))
    print round_op(mult)(*(args + [gmpy2.RoundUp]))
