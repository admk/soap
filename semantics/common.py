#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


import numpy as np


def get_exponent(v):
    if isinstance(v, np.float32):
        mask, shift, offset = 0x7f800000, 23, 127
    else:
        raise NotImplementedError('The value v can only be of type np.float32')
    return ((v.view('i') & mask) >> shift) - offset


def ulp(v):
    if isinstance(v, np.float16):
        prec = 11
    elif isinstance(v, np.float32):
        prec = 24
    elif isinstance(v, np.float64):
        prec = 53
    return 2 ** (get_exponent(v) - prec)


def round(v, m='Nearest'):
    pass


if __name__ == '__main__':
    v = np.float32('2.5')
    print get_exponent(v)
    print ulp(v)
