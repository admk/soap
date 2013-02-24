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
    pass


def round(v, m='Nearest'):
    pass


if __name__ == '__main__':
    print get_exponent(np.float32('2.5'))
