from contextlib import contextmanager

from soap.common.base import DynamicMethods, Comparable
from soap.common.cache import invalidate_cache, cached, Flyweight
from soap.common.profile import timeit, timed, profiled


@contextmanager
def ignored(*exceptions):
    try:
        yield
    except exceptions:
        pass
