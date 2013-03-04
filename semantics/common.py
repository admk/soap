#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


import gmpy2
from gmpy2 import mpq, mpfr


def ulp(v):
    return mpq(2) ** v.as_mantissa_exp()[1]


def round(mode):
    def decorator(f):
        def wrapped(v1, v2):
            with gmpy2.local_context(round=mode):
                return f(v1, v2)
        return wrapped
    return decorator


if __name__ == '__main__':
    gmpy2.set_context(gmpy2.ieee(32))
    print float(ulp(mpfr('0.1')))
    mult = lambda x, y: x * y
    args = [mpfr('0.3'), mpfr('2.6')]
    print round(gmpy2.RoundDown)(mult)(*args)
    print round(gmpy2.RoundUp)(mult)(*args)
