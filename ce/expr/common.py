#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


from __future__ import print_function


ADD_OP = '+'
MULTIPLY_OP = '*'

OPERATORS = [ADD_OP, MULTIPLY_OP]

ASSOCIATIVITY_OPERATORS = [ADD_OP, MULTIPLY_OP]

COMMUTATIVITY_OPERATORS = ASSOCIATIVITY_OPERATORS

COMMUTATIVE_DISTRIBUTIVITY_OPERATOR_PAIRS = [(MULTIPLY_OP, ADD_OP)]
# left-distributive: a * (b + c) == a * b + a * c
LEFT_DISTRIBUTIVITY_OPERATOR_PAIRS = \
    COMMUTATIVE_DISTRIBUTIVITY_OPERATOR_PAIRS
# Note that division '/' is only right-distributive over +
RIGHT_DISTRIBUTIVITY_OPERATOR_PAIRS = \
    COMMUTATIVE_DISTRIBUTIVITY_OPERATOR_PAIRS

LEFT_DISTRIBUTIVITY_OPERATORS, LEFT_DISTRIBUTION_OVER_OPERATORS = \
    zip(*LEFT_DISTRIBUTIVITY_OPERATOR_PAIRS)
RIGHT_DISTRIBUTIVITY_OPERATORS, RIGHT_DISTRIBUTION_OVER_OPERATORS = \
    zip(*RIGHT_DISTRIBUTIVITY_OPERATOR_PAIRS)


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


def is_exact(v):
    from ..semantics import mpq_type
    return isinstance(v, (int, long, mpq_type))


def is_expr(e):
    from parser import Expr
    return isinstance(e, Expr)
