#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


__author__ = 'Xitong Gao'
__email__ = 'xtg08@ic.ac.uk'




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
