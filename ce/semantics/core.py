#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


__author__ = 'Xitong Gao'
__email__ = 'xtg08@ic.ac.uk'


import itertools
import gmpy2
from gmpy2 import mpq, mpfr, RoundUp, RoundDown

from common import mpfr_type, mpq_type, round_op, round_off_error


class Interval(object):

    def __init__(self, (min_val, max_val)):
        self.min, self.max = min_val, max_val
        if type(min_val) != type(max_val):
            raise TypeError('min_val and max_val must be of the same type')

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

    def __hash__(self):
        return hash(tuple(self))


class FloatInterval(Interval):

    def __init__(self, (min_val, max_val)):
        if type(min_val) is str:
            with gmpy2.local_context(round=RoundDown):
                min_val = mpfr(min_val)
        if type(max_val) is str:
            with gmpy2.local_context(round=RoundUp):
                max_val = mpfr(max_val)
        super(FloatInterval, self).__init__((min_val, max_val))
        if type(min_val) is not mpfr_type or type(max_val) is not mpfr_type:
            raise TypeError('min_val and max_val must be mpfr values')

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

    def __init__(self, (min_val, max_val)):
        if type(min_val) is str:
            min_val = mpq(min_val)
        if type(max_val) is str:
            max_val = mpq(max_val)
        super(FractionInterval, self).__init__((min_val, max_val))
        if type(min_val) is not mpq_type or type(max_val) is not mpq_type:
            raise TypeError('min_val and max_val must be mpq values')

    def __str__(self):
        return '[~%s, ~%s]' % (str(mpfr(self.min)), str(mpfr(self.max)))


class ErrorSemantics(object):

    def __init__(self, (v_min, v_max), (e_min, e_max)):
        self.v = FloatInterval([v_min, v_max])
        self.e = FractionInterval([e_min, e_max])

    def __add__(self, other):
        v = self.v + other.v
        e = self.e + other.e + round_off_error(v)
        return ErrorSemantics([v.min, v.max], [e.min, e.max])

    def __sub__(self, other):
        v = self.v - other.v
        e = self.e - other.e + round_off_error(v)
        return ErrorSemantics([v.min, v.max], [e.min, e.max])

    def __mul__(self, other):
        v = self.v * other.v
        e = self.e * other.e + round_off_error(v)
        e += FractionInterval([mpq(self.v.min), mpq(self.v.max)]) * other.e
        e += FractionInterval([mpq(other.v.min), mpq(other.v.max)]) * self.e
        return ErrorSemantics([v.min, v.max], [e.min, e.max])

    def __str__(self):
        return '%sx%s' % (self.v, self.e)

    def __repr__(self):
        return 'ErrorSemantics([%s, %s], [%s, %s])' % \
            (repr(self.v.min), repr(self.v.max),
             repr(self.e.min), repr(self.e.max))

    def __hash__(self):
        return hash((self.v, self.e))


def cast(v, w=None):
    w = w if w else v
    return ErrorSemantics([v, w], round_off_error(FractionInterval([v, w])))


if __name__ == '__main__':
    gmpy2.set_context(gmpy2.ieee(32))
    print FloatInterval(['0.1', '0.2']) * FloatInterval(['5.3', '6.7'])
    a, b = cast('0.3', '0.6'), cast('0.3')
    print a, b, a * b
