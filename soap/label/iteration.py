from soap.lattice.flat import denotational


class Iteration(denotational(int)):
    """
    FIXME This should be a finite total order instead of a flat lattice.

    What was I thinking.
    """
    __slots__ = ()

    def __init__(self, value=None, top=False, bottom=False):
        if bottom:
            value = 0
            bottom = False
        super().__init__(value=value, top=top, bottom=bottom)

    def is_top(self):
        # return self > SOME_TODO_GLOBAL_VALUE
        return False

    def is_bottom(self):
        return self.v == 0
