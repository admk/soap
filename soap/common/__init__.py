from contextlib import contextmanager

from soap.common.base import DynamicMethods, Comparable
from soap.common.cache import invalidate_cache, cached, Flyweight
from soap.common.profile import timeit, timed, profiled
from soap.common.label import (
    fresh_int, Label, Iteration, Annotation, Identifier
)


@contextmanager
def ignored(*exceptions):
    try:
        yield
    except exceptions:
        pass


_superscript_map = (
    '        ⁽⁾  \'   ⁰¹²³⁴⁵⁶⁷⁸⁹       ᴬᴮ ᴰᴱ ᴳᴴᴵᴶᴷᴸᴹᴺᴼᴾ ᴿ ᵀᵁⱽᵂ         '
    'ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖ ʳˢᵗᵘᵛʷˣʸᶻ    ')


def superscript(value):
    supped = ''
    for d in str(value):
        d = 'T' if d == '⊤' else d
        d = '0' if d == '⊥' else d
        try:
            supped += _superscript_map[ord(d) - 32]
        except IndexError:
            raise ValueError('Failed to convert {}'.format(d))
    return supped
