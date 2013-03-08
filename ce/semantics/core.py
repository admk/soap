#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


__author__ = 'Xitong Gao'
__email__ = 'xtg08@ic.ac.uk'


import itertools
import gmpy2
from gmpy2 import RoundUp, RoundDown

from . import mpfr, mpq
from common import round_op, round_off_error


class Interval(object):

    def __init__(self, v):
        min_val, max_val = v
        self.min, self.max = min_val, max_val

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
        super(FloatInterval, self).__init__((min_val, max_val))

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
        l = itertools.product((self.min, other.min),
                              (self.max, other.max),
                              (RoundDown, RoundUp))
        v = [f(x, y, m) for x, y, m in l]
        return Interval([min(v), max(v)])


class FractionInterval(Interval):

    def __init__(self, v):
        min_val, max_val = v
        super(FractionInterval, self).__init__((mpq(min_val), mpq(max_val)))

    def __str__(self):
        return '[~%s, ~%s]' % (str(mpfr(self.min)), str(mpfr(self.max)))


class ErrorSemantics(object):

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

    def __hash__(self):
        return hash((self.v, self.e))


if __name__ == '__main__':
    gmpy2.set_context(gmpy2.ieee(32))
    print FloatInterval(['0.1', '0.2']) * FloatInterval(['5.3', '6.7'])
