import weakref
import pickle
import functools


_cached_funcs = []


def process_invalidate_cache():
    for f in _cached_funcs:
        f.cache_clear()
    Flyweight._cache.clear()


def invalidate_cache():
    from soap import logger
    from soap.common.parallel import pool
    process_invalidate_cache()
    pool.invalidate_cache()
    logger.info('Cache invalidated.')


def cached(f):
    class NonLocals(object):
        pass
    CACHE_CAPACITY = 1000000
    cache = {}
    NonLocals.full = False
    NonLocals.hits = NonLocals.misses = NonLocals.currsize = 0
    NonLocals.root = []
    NonLocals.root[:] = [NonLocals.root, NonLocals.root, None, None]
    PREV, NEXT, KEY, RESULT = range(4)

    def decorated(*args, **kwargs):
        if not kwargs:
            key_tuple = args
        else:
            key_tuple = (args, tuple(sorted(kwargs.items(), key=hash)))
        key = pickle.dumps(key_tuple)
        link = cache.get(key)
        if link is not None:
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
    d.wrapped_func = f

    global _cached_funcs
    _cached_funcs.append(d)

    return d


def dump_cache_info():
    from soap import logger
    logger.info('Cache Hits and Misses')
    logger.info('Name\tHits\tMisses\tRate\tSize')
    for func in _cached_funcs:
        hits, misses, size = func.cache_info()
        if hits or misses:
            rate = '{}'.format(int(100 * hits / (hits + misses)))
            logger.info('{}\n\t\t{}\t{}\t{}%\t{}'.format(
                func.__qualname__, hits, misses, rate, size))


class Flyweight(object):

    _cache = weakref.WeakValueDictionary()

    def __new__(cls, *args, **kwargs):
        if not args and not kwargs:
            return object.__new__(cls)
        key = pickle.dumps((cls, args, list(kwargs.items())))
        v = cls._cache.get(key, None)
        if v is not None:
            return v
        v = object.__new__(cls)
        cls._cache[key] = v
        return v


class cached_property(object):
    """
    Cached property descriptor.
    https://github.com/pydanny/cached-property
    """
    def __init__(self, func):
        self.__doc__ = getattr(func, '__doc__')
        self.func = func

    def __get__(self, obj, cls):
        if obj is None:
            return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value
