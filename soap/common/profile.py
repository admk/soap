import time
import functools
from contextlib import contextmanager


def timeit(f):
    from soap import logger
    def timed(*args, **kwargs):
        ts = time.time()
        result = f(*args, **kwargs)
        te = time.time()
        logger.info('%r %f sec' % (f.__name__, te - ts))
        return result
    return functools.wraps(f)(timed)


@contextmanager
def timed(name=''):
    from soap import logger
    ts = time.time()
    yield
    te = time.time()
    logger.info('%s %f sec' % (name, te - ts))


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
