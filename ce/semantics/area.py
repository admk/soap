#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


from ..common import Comparable
import ce.expr

from . import Lattice


class AreaSemantics(Comparable, Lattice):

    def __init__(self, e):
        self.e = e
        self.l, self.s = e.as_labels()
        super(AreaSemantics, self).__init__()

    def join(self, other):
        pass

    def meet(self, other):
        pass

    @property
    def area(self):
        mult, add = 0, 0
        for _, e in self.s.iteritems():
            try:
                if e.op == ce.expr.MULTIPLY_OP:
                    mult += 1
                if e.op == ce.expr.ADD_OP:
                    add += 1
            except AttributeError:
                pass
        return {
            ce.expr.MULTIPLY_OP: mult,
            ce.expr.ADD_OP: add
        }

    def __add__(self, other):
        return AreaSemantics(self.e + other.e)

    def __sub__(self, other):
        return AreaSemantics(self.e - other.e)

    def __mul__(self, other):
        return AreaSemantics(self.e * other.e)

    def __lt__(self, other):
        if not isinstance(other, AreaSemantics):
            return False
        if self.area[ce.expr.MULTIPLY_OP] > other.area[ce.expr.MULTIPLY_OP]:
            return False
        if self.area[ce.expr.MULTIPLY_OP] == other.area[ce.expr.MULTIPLY_OP]:
            if self.area[ce.expr.ADD_OP] >= other.area[ce.expr.ADD_OP]:
                return False
        return True

    def __eq__(self, other):
        if not isinstance(other, AreaSemantics):
            return False
        if self.area != other.area:
            return False
        return True

    def __str__(self):
        return str(self.area)

    def __repr__(self):
        return 'AreaSemantics(%s)' % repr(self.e)


if __name__ == '__main__':
    e = ce.expr.Expr('((a + 1) * (a + 1))')
    print AreaSemantics(e)
