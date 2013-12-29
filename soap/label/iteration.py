from soap.context import context

from soap.lattice.base import Lattice


class Iteration(Lattice, int):
    """
    FIXME This should be a finite total order instead of a flat lattice.

    What was I thinking.
    """
    __slots__ = ()

    def __init__(self, value=None, top=False, bottom=False):
        if top:
            value = 1000
        if bottom:
            value = 0
        super().__init__(value)

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
