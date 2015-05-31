from contextlib import contextmanager

from soap.common.base import DynamicMethods, Comparable, base_dispatcher
from soap.common.cache import (
    invalidate_cache, cached, cached_property, Flyweight
)
from soap.common.formatting import underline, superscript, indent, code_gobble
from soap.common.profile import timeit, timed, profile_calls, profile_memory


@contextmanager
def ignored(*exceptions):
    try:
        yield
    except exceptions:
        pass
