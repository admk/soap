from contextlib import contextmanager

from soap.common.base import DynamicMethods, Comparable
from soap.common.cache import invalidate_cache, cached, Flyweight
from soap.common.profile import timeit, timed, profiled
from soap.common.label import fresh_int, Label, FlowLabel, Labels


@contextmanager
def ignored(*exceptions):
    try:
        yield
    except exceptions:
        pass
