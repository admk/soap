#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


from ..common import Comparable

from .common import ADD_OP, MULTIPLY_OP, OPERATORS, ASSOCIATIVITY_OPERATORS, \
    is_exact, cached
from ..semantics import mpq, cast_error, cast_error_constant, Label


def _try_to_number(s):
    try:
        return mpq(s)
    except (ValueError, TypeError):
        return s


def _parse_r(s):
    s = s.strip()
    bracket_level = 0
    operator_pos = -1
    for i, v in enumerate(s):
        if v == '(':
            bracket_level += 1
        if v == ')':
            bracket_level -= 1
        if bracket_level == 1 and v in OPERATORS:
            operator_pos = i
            break
    if operator_pos == -1:
        return s
    a1 = _parse_r(s[1:operator_pos].strip())
    a2 = _parse_r(s[operator_pos + 1:-1].strip())
    return Expr(string=None, op=s[operator_pos], a1=a1, a2=a2)


class Expr(Comparable):

    def __init__(self, string=None, op=None, a1=None, a2=None):
        if string:
            expr = _parse_r(string)
            self.op = expr.op
            self.a1 = expr.a1
            self.a2 = expr.a2
        else:
            self.op = op
            self.a1 = _try_to_number(a1)
            self.a2 = _try_to_number(a2)
        super(Expr, self).__init__()

    def tree(self):
        def to_tuple(a):
            if isinstance(a, Expr):
                return a.tree()
            return a
        return (self.op, to_tuple(self.a1), to_tuple(self.a2))

    def tuple(self):
        return (self.op, self.a1, self.a2)

    @cached
    def error(self, v):
        def eval(a):
            if isinstance(a, Expr):
                return a.error(v)
            if isinstance(a, str):
                return v[a]
            if is_exact(a):
                return cast_error_constant(a)
        e1, e2 = eval(self.a1), eval(self.a2)
        if self.op == ADD_OP:
            return e1 + e2
        if self.op == MULTIPLY_OP:
            return e1 * e2

    def equiv(self, other):
        def eq(a, b):
            try:
                return a.equiv(b)
            except AttributeError:
                try:
                    return b.equiv(a)
                except AttributeError:
                    return a == b
        if not isinstance(other, Expr):
            return False
        if eq(self.a1, other.a1) and eq(self.a2, other.a2):
            return True
        if not self.op in COMMUTATIVITY_OPERATORS:
            return False
        if eq(self.a1, other.a2) and eq(self.a2, other.a1):
            return True
        return False

    @cached
    def as_labels(self):
        def to_label(e):
            if isinstance(e, Expr):
                return e.as_labels()
            else:
                l = Label(e)
                return l, {l: e}
        l1, s1 = to_label(self.a1)
        l2, s2 = to_label(self.a2)
        e = BExpr(op=self.op, a1=l1, a2=l2)
        l = Label(e)
        s = {l: e}
        s.update(s1)
        s.update(s2)
        return l, s

    @cached
    def area(self):
        from ..semantics import AreaSemantics
        return AreaSemantics(self)

    def __iter__(self):
        return iter(self.tuple())

    def __str__(self):
        return '(%s %s %s)' % (str(self.a1), self.op, str(self.a2))

    def __repr__(self):
        return "Expr(op='%s', a1=%s, a2=%s)" % \
            (self.op, repr(self.a1), repr(self.a2))

    def __add__(self, other):
        return Expr(op=ADD_OP, a1=self, a2=other)

    def __mul__(self, other):
        return Expr(op=MULTIPLY_OP, a1=self, a2=other)

    def __eq__(self, other):
        if not isinstance(other, Expr):
            return False
        return self.tuple() == other.tuple()

    def __lt__(self, other):
        if not isinstance(other, Expr):
            return False
        return self.tuple() < other.tuple()

    def __hash__(self):
        return hash(self.tuple())


class BExpr(Expr):

    def __init__(self, **kwargs):
        super(BExpr, self).__init__(**kwargs)
        if not isinstance(self.a1, Label) or not isinstance(self.a2, Label):
            raise ValueError('BExpr allows only binary expressions.')
        self.a1, self.a2 = sorted([self.a1, self.a2])


if __name__ == '__main__':
    r = Expr('((a + 1) * ((a + 1) + b))')
    for i in range(3):
        print(r.error({
            'a': cast_error('0.2', '0.3'),
            'b': cast_error('2.3', '2.4')}))
    for e, v in r.as_labels()[1].items():
        print(str(e), ':', str(v))
    print(r.area())
