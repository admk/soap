from contextlib import contextmanager

from soap.common.base import DynamicMethods, Comparable
from soap.common.cache import invalidate_cache, cached, Flyweight
from soap.common.profile import timeit, timed, profiled
from soap.common.label import fresh_int, Label


@contextmanager
def ignored(*exceptions):
    try:
        yield
    except exceptions:
        pass


def superscript(value):
    value = str(value)
    if not value.isdigit():
        raise ValueError(
            'Value {!r} is not decimal, cannot convert to superscript.'
            ''.format(value))
    return ''.join('⁰¹²³⁴⁵⁶⁷⁸⁹'[int(d)] for d in value)
