#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


__author__ = 'Xitong Gao'
__email__ = 'xtg08@ic.ac.uk'


import decimal
decimal.getcontext().traps[decimal.Inexact] = True


class ExactDecimal(decimal.Decimal):

    def __init__(self, v):
        if not isinstance(v, str):
            raise ValueError('Value is not string, could be inexact')
        super(ExactDecimal, self).__init__(v)

    def _exact_operation(self, op, other):
        while True:
            try:
                return decimal.Decimal.__dict__['__%s__' % op](self, other)
            except decimal.Inexact:
                decimal.getcontext().prec += 1

    def __add__(self, other):
        return self._exact_operation('add', other)

    def __sub__(self, other):
        return self._exact_operation('sub', other)

    def __mul__(self, other):
        return self._exact_operation('mul', other)


class AbstractInterval(object):

    def __init__(self, min_val, max_val):
        pass
        

class AbstractErrorSemantics(object):

    def __init__(self, ):
        pass


if __name__ == '__main__':
    print ExactDecimal('2.89638143766236577531434781') / \
            ExactDecimal('6.7952943728618031095770')
    print decimal.getcontext().prec
