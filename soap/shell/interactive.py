from pprint import pprint

import soap
from soap import *


def main():
    def pp(*args):
        for a in args:
            pprint(a)

    def pr(*args):
        with context.local(repr='repr'):
            pp(*args)

    def ps(*args):
        with context.local(repr='str'):
            pp(*args)

    class __IntervalShortcut(object):
        def __init__(self, cls):
            self.cls = cls

        def __getitem__(self, key):
            return self.cls(key)

    I = Int = IntegerInterval
    F = Float = FloatInterval
    E = Error = ErrorSemantics
    S = Box = BoxState
    M = Meta = MetaState
    i = __IntervalShortcut(IntegerInterval)
    f = __IntervalShortcut(FloatInterval)
    e = __IntervalShortcut(ErrorSemantics)
    s = BoxState()
    m = MetaState()
    ctx = context

    with context.no_invalidate_cache():
        context.repr = str

    return shell.shell()
