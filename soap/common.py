import inspect
import time
import functools
import weakref
import pickle
from contextlib import contextmanager

import soap.logger as logger


class DynamicMethods(object):

    @classmethod
    def list_method_names(cls, predicate):
        """Find all transform methods within the class that satisfies the
        predicate.

        Returns:
            A list of tuples containing method names.
        """
        methods = [member[0] for member in inspect.getmembers(cls,
                   predicate=inspect.isroutine)]
        return [m for m in methods if not m.startswith('_') and
                'list_method' not in m and predicate(m)]

    def list_methods(self, predicate):
        return [getattr(self, m) for m in self.list_method_names(predicate)]


class Comparable(object):

    def __ne__(self, other):
        return not self.__eq__(other)

    def __ge__(self, other):
        return not self.__lt__(other)

    def __gt__(self, other):
        return not self.__eq__(other) and not self.__lt__(other)

    def __le__(self, other):
        return not self.__gt__(other)


def timeit(f):
    def timed(*args, **kwargs):
        ts = time.time()
        result = f(*args, **kwargs)
        te = time.time()
        logger.info('%r %f sec' % (f.__name__, te - ts))
        return result
    return functools.wraps(f)(timed)


@contextmanager
def timed(name=''):
    ts = time.time()
    yield
    te = time.time()
    logger.info('%s %f sec' % (name, te - ts))


@contextmanager
def ignored(*exceptions):
    try:
        yield
    except exceptions:
        pass


@contextmanager
def profiled():
    import pycallgraph
    from pympler.classtracker import ClassTracker
    from pympler.asizeof import asizeof
    from soap.common import Flyweight, _cache_map
    from soap.expression import Expr
    pycallgraph.start_trace()
    tracker = ClassTracker()
    tracker.track_object(Flyweight._cache)
    tracker.track_class(Expr)
    yield
    tracker.create_snapshot()
    tracker.stats.print_summary()
    print('Flyweight cache size', asizeof(Flyweight._cache))
    print('Global cache size', asizeof(_cache_map))
    pycallgraph.make_dot_graph('profile.png')


_cached_funcs = []


def _process_invalidate_cache():
    for f in _cached_funcs:
        f.cache_clear()
    Flyweight._cache.clear()


def invalidate_cache():
    from soap.transformer.core import pool
    _process_invalidate_cache()
    pool().apply(_process_invalidate_cache)


def cached(f):
    CACHE_CAPACITY = 1000
    cache = {}
    full = False
    hits = misses = currsize = 0
    root = []
    root[:] = [root, root, None, None]
    PREV, NEXT, KEY, RESULT = range(4)

    def decorated(*args, **kwargs):
        nonlocal root, hits, misses, currsize, full
        key = pickle.dumps((f.__name__, args, tuple(kwargs.items())))
        link = cache.get(key)
        if not link is None:
            p, n, k, r = link
            p[NEXT] = n
            n[PREV] = p
            last = root[PREV]
            last[NEXT] = root[PREV] = link
            link[PREV] = last
            link[NEXT] = root
            hits += 1
            return r
        r = f(*args, **kwargs)
        if full:
            root[KEY] = key
            root[RESULT] = r
            cache[key] = root
            root = root[NEXT]
            del cache[root[KEY]]
            root[KEY] = root[RESULT] = None
        else:
            last = root[PREV]
            link = [last, root, key, r]
            cache[key] = last[NEXT] = root[PREV] = link
            currsize += 1
            full = (currsize == CACHE_CAPACITY)
        misses += 1
        return r

    def cache_info():
        return hits, misses, currsize

    def cache_clear():
        nonlocal hits, misses, currsize, full
        cache.clear()
        root[:] = [root, root, None, None]
        hits = misses = currsize = 0
        full = False

    d = functools.wraps(f)(decorated)
    d.cache_info = cache_info
    d.cache_clear = cache_clear

    global _cached_funcs
    _cached_funcs.append(d)

    return d


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


_label_count = 0
_label_map = None


def fresh_int(e=None):
    """Generates a fresh int for the label of the expression `e`."""
    def _incr():
        global _label_count
        _label_count += 1
        return _label_count
    global _label_map
    _label_map = _label_map or {}
    if e is not None and e in _label_map:
        return _label_map[e]
    l = _incr()
    if e is not None:
        _label_map[e] = l
    return l


class Label(object):
    """Constructs a label for the expression `e`"""
    def __init__(self, e=None, l=None, desc=None):
        self.l = l or fresh_int(e)
        self.e = e
        self.desc = desc
        self.__slots__ = []
        super().__init__()

    def signal_name(self):
        return 's_%d' % self.l

    def port_name(self):
        from soap.expression.common import OPERATORS
        forbidden = OPERATORS + [',', '(', ')', '[', ']']
        if any(k in str(self.e) for k in forbidden):
            s = self.l
        else:
            s = self.e
        return 'p_%s' % str(s)

    def __str__(self):
        s = 'l{}'.format(self.l)
        if self.desc:
            s += ':{.desc}'.format(self)
        return s

    def __repr__(self):
        return 'Label(%s, %s)' % (repr(self.e), repr(self.l))

    def __eq__(self, other):
        if not isinstance(other, Label):
            return False
        return self.l == other.l

    def __lt__(self, other):
        if not isinstance(other, Label):
            return False
        return self.l < other.l

    def __hash__(self):
        return hash(self.l)


class Labels(object):
    """Not used... Check if this can be removed."""
    def __init__(self, s):
        self.s = {fresh_int: e for e in s}
        super().__init__()

    def add(self, e):
        if e in list(self.s.items()):
            return
        self.s[Label()] = e
