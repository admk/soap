from soap.context import context
from soap.lattice.base import Lattice


class Iteration(Lattice, int):
    """
    Iteration, interger bounded from 0 (current), aka bottom, to
    context.program_depth, aka top. It is a total ordering.

    Methods __hash__, __str__ and __repr__ are necessary because of the MRO.
    """
    __slots__ = ()

    def __new__(cls, value=None, top=False, bottom=False):
        if top:
            value = 1000
        if bottom:
            value = 0
        return super().__new__(cls, value)

    def is_top(self):
        return int(self) > context.program_depth

    def is_bottom(self):
        return int(self) == 0

    def join(self, other):
        return self.__class__(max(self, other))

    def meet(self, other):
        return self.__class__(min(self, other))

    def le(self, other):
        return int(self) <= int(other)

    def __add__(self, other):
        return self.__class__(int(self) + int(other))

    def __sub__(self, other):
        raise NotImplementedError
    __rsub__ = __sub__

    def __hash__(self):
        return hash((self.__class__, int(self)))

    def __str__(self):
        return str(int(self))

    def __repr__(self):
        return '{cls}({val!r})'.format(
            cls=self.__class__.__name__, val=int(self))
