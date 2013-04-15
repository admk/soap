import functools
import weakref
import pickle


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
    list(zip(*LEFT_DISTRIBUTIVITY_OPERATOR_PAIRS))
RIGHT_DISTRIBUTIVITY_OPERATORS, RIGHT_DISTRIBUTION_OVER_OPERATORS = \
    list(zip(*RIGHT_DISTRIBUTIVITY_OPERATOR_PAIRS))


CACHE_CAPACITY = 1000000
_cache_map = dict()


def cached(f):
    def decorated(*args, **kwargs):
        key = pickle.dumps((f.__name__, args, tuple(kwargs.items())))
        v = _cache_map.get(key)
        if v is None:
            v = f(*args, **kwargs)
        if len(_cache_map) < CACHE_CAPACITY:
            _cache_map[key] = v
        return v
    return functools.wraps(f)(decorated)


class Flyweight(object):
    _cache = weakref.WeakValueDictionary()

    def __new__(cls, *args, **kwargs):
        if not args and not kwargs:
            return object.__new__(cls)
        key = pickle.dumps((cls, args, list(kwargs.items())))
        v = cls._cache.get(key, None)
        if v:
            return v
        v = object.__new__(cls)
        cls._cache[key] = v
        return v


def is_exact(v):
    from ..semantics import mpq_type
    return isinstance(v, (int, mpq_type))


def is_expr(e):
    from .biop import Expr
    return isinstance(e, Expr)
