import weakref
import pickle
import functools


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
    class NonLocals(object):
        pass
    CACHE_CAPACITY = 1000
    cache = {}
    NonLocals.full = False
    NonLocals.hits = NonLocals.misses = NonLocals.currsize = 0
    NonLocals.root = []
    NonLocals.root[:] = [NonLocals.root, NonLocals.root, None, None]
    PREV, NEXT, KEY, RESULT = range(4)

    def decorated(*args, **kwargs):
        key = pickle.dumps((f.__name__, args, tuple(kwargs.items())))
        link = cache.get(key)
        if not link is None:
            p, n, k, r = link
            p[NEXT] = n
            n[PREV] = p
            last = NonLocals.root[PREV]
            last[NEXT] = NonLocals.root[PREV] = link
            link[PREV] = last
            link[NEXT] = NonLocals.root
            NonLocals.hits += 1
            return r
        r = f(*args, **kwargs)
        if NonLocals.full:
            NonLocals.root[KEY] = key
            NonLocals.root[RESULT] = r
            cache[key] = NonLocals.root
            NonLocals.root = NonLocals.root[NEXT]
            del cache[NonLocals.root[KEY]]
            NonLocals.root[KEY] = NonLocals.root[RESULT] = None
        else:
            last = NonLocals.root[PREV]
            link = [last, NonLocals.root, key, r]
            cache[key] = last[NEXT] = NonLocals.root[PREV] = link
            NonLocals.currsize += 1
            NonLocals.full = (NonLocals.currsize == CACHE_CAPACITY)
        NonLocals.misses += 1
        return r

    def cache_info():
        return NonLocals.hits, NonLocals.misses, NonLocals.currsize

    def cache_clear():
        cache.clear()
        NonLocals.root[:] = [NonLocals.root, NonLocals.root, None, None]
        NonLocals.hits = NonLocals.misses = NonLocals.currsize = 0
        NonLocals.full = False

    d = functools.wraps(f)(decorated)
    d.cache_info = cache_info
    d.cache_clear = cache_clear

    global _cached_funcs
    _cached_funcs.append(d)

    return d


class Flyweight(object):

    __slots__ = ('__weakref__', )
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
