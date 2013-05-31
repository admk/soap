import math
import gmpy2

import ce.expr
from ce.common import Comparable
from ce.semantics import Lattice
from ce.semantics import flopoco


class AreaSemantics(Comparable, Lattice):

    def __init__(self, e, v, p):
        self.e = e
        self.v = v
        self.p = p
        self.l, self.s = e.as_labels()
        self.area = self._area()
        super().__init__()

    def join(self, other):
        pass

    def meet(self, other):
        pass

    def _op_counts(self):
        mult, add = 0, 0
        for _, e in self.s.items():
            try:
                if e.op == ce.expr.MULTIPLY_OP:
                    mult += 1
                if e.op == ce.expr.ADD_OP:
                    add += 1
            except AttributeError:
                pass
        return mult, add

    def _area(self):
        b = self.e.error(self.v, self.p).v
        bmax = max(abs(b.min), abs(b.max))
        expmax = math.floor(math.log(bmax, 2))
        we = int(math.ceil(math.log(expmax + 1, 2) + 1))
        we = max(we, flopoco.we_min)
        wf = self.p
        mult, add = self._op_counts()
        return flopoco.adder(we, wf) * add + flopoco.multiplier(we, wf) * mult

    def __add__(self, other):
        return AreaSemantics(self.e + other.e, self.v)

    def __sub__(self, other):
        return AreaSemantics(self.e - other.e, self.v)

    def __mul__(self, other):
        return AreaSemantics(self.e * other.e, self.v)

    def __lt__(self, other):
        if not isinstance(other, AreaSemantics):
            return False
        return self.area < other.area

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
    gmpy2.set_context(gmpy2.ieee(128))
    gmpy2.get_context().precision = 24
    e = ce.expr.Expr('((a + 1) * (a + 1))')
    v = {'a': ['0.2', '0.3']}
    print(AreaSemantics(e, v))
