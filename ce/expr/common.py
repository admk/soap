#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


from __future__ import print_function


ADD_OP = '+'
MULTIPLY_OP = '*'

OPERATORS = [ADD_OP, MULTIPLY_OP]


_cache_map = dict()


def cached(f):
    def decorated(*args, **kwargs):
        key = (f, tuple(args), tuple(kwargs.items()))
        if key in _cache_map:
            return _cache_map[key]
        v = f(*args, **kwargs)
        _cache_map[key] = v
        return v
    return decorated
