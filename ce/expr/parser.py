#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


from ..common import Comparable

from .common import ADD_OP, MULTIPLY_OP, OPERATORS, ASSOCIATIVITY_OPERATORS, \
    COMMUTATIVITY_OPERATORS, is_exact, cached, Flyweight
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


class Expr(Comparable, Flyweight):

    __slots__ = ('op', 'a1', 'a2', '_hash')

    def __init__(self, *args, **kwargs):
        if kwargs:
            op = kwargs.setdefault('op')
            a1 = kwargs.setdefault('a1')
            a2 = kwargs.setdefault('a2')
            al = a1, a2
        if len(args) == 1:
            expr = _parse_r(list(args).pop())
            op, al = expr.op, expr.args
        elif len(args) == 2:
            op, al = args
        elif len(args) == 3:
            op, *al = args
        self.op = op
        self.a1, self.a2 = [_try_to_number(a) for a in al]
        super(Expr, self).__init__()

    def tree(self):
        def to_tuple(a):
            if isinstance(a, Expr):
                return a.tree()
            return a
        return (self.op, to_tuple(self.a1), to_tuple(self.a2))

    @property
    def args(self):
        return [self.a1, self.a2]

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
        return iter((self.op, self.a1, self.a2))

    def __str__(self):
        return '(%s %s %s)' % (str(self.a1), self.op, str(self.a2))

    def __repr__(self):
        return "Expr(op='%s', a1=%s, a2=%s)" % \
            (self.op, repr(self.a1), repr(self.a2))

    def __add__(self, other):
        return Expr(op=ADD_OP, a1=self, a2=other)

    def __mul__(self, other):
        return Expr(op=MULTIPLY_OP, a1=self, a2=other)

    def _symmetric_id(self):
        if self.op in COMMUTATIVITY_OPERATORS:
            _sym_id = (self.op, frozenset(self.args))
        else:
            _sym_id = tuple(self)
        return _sym_id

    def __eq__(self, other):
        if not isinstance(other, Expr):
            return False
        if self.op != other.op:
            return False
        if hash(self) != hash(other):
            return False
        if id(self) == id(other):
            return True
        return self._symmetric_id() == other._symmetric_id()

    def __lt__(self, other):
        if not isinstance(other, Expr):
            return False
        return self._symmetric_id() < other._symmetric_id()

    def __hash__(self):
        try:
            return self._hash
        except AttributeError:
            pass
        self._hash = hash(self._symmetric_id())
        return self._hash


class BExpr(Expr):

    __slots__ = Expr.__slots__

    def __init__(self, **kwargs):
        super(BExpr, self).__init__(**kwargs)
        if not isinstance(self.a1, Label) or not isinstance(self.a2, Label):
            raise ValueError('BExpr allows only binary expressions.')


if __name__ == '__main__':
    r = Expr('((a + 1) * ((a + 1) + b))')
    for i in range(3):
        print(r.error({
            'a': cast_error('0.2', '0.3'),
            'b': cast_error('2.3', '2.4')}))
    for e, v in r.as_labels()[1].items():
        print(str(e), ':', str(v))
    print(r.area())
