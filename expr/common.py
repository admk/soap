#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


from __future__ import print_function


ADD_OP = '+'
MULTIPLY_OP = '*'

OPERATORS = [ADD_OP, MULTIPLY_OP]


def pprint_expr_trees(trees):
    print('[')
    for t in trees:
        print(' ', t)
    print(']')
