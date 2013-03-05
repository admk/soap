#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


from __future__ import print_function


ADD_OP = '+'
MULTIPLY_OP = '*'

OPERATORS = [ADD_OP, MULTIPLY_OP]


def to_immutable(*m):
    def r(d):
        if isinstance(d, dict):
            return tuple((e, to_immutable(v)) for e, v in d.iteritems())
        if isinstance(d, (list, tuple)):
            return tuple(to_immutable(e) for e in d)
        return repr(d)
    return tuple(r(e) for e in m)


_cache_map = dict()


def cached(f):
    def decorated(*args, **kwargs):
        key = to_immutable(f, args, kwargs.items())
        if key in _cache_map:
            return _cache_map[key]
        v = f(*args, **kwargs)
        _cache_map[key] = v
        return v
    return decorated
