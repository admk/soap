#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


from common import OPERATORS, cached


def _to_number(s):
    try:
        return long(s)
    except ValueError:
        return float(s)


def _try_to_number(s):
    try:
        return _to_number(s)
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


class Expr(object):

    def __init__(self, string=None, op=None, a1=None, a2=None):
        super(Expr, self).__init__()
        if string:
            expr = _parse_r(string)
            self.op = expr.op
            self.a1 = expr.a1
            self.a2 = expr.a2
        else:
            self.op = op
            self.a1 = _try_to_number(a1)
            self.a2 = _try_to_number(a2)

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
        pass

    def __iter__(self):
        return iter(self.tuple())

    def __str__(self):
        return '(%s %s %s)' % (str(self.a1), self.op, str(self.a2))

    def __repr__(self):
        return "Expr(op='%s', a1=%s, a2=%s)" % \
            (self.op, repr(self.a1), repr(self.a2))

    def __eq__(self, other):
        if not isinstance(other, Expr):
            return False
        return self.tuple() == other.tuple()

    def __hash__(self):
        return hash(self.tuple())


if __name__ == '__main__':
    s = '((a + 1) * c)'
    r = Expr(s)
    t = repr(r)
    t = eval(t)
    assert(r == t)
    assert(s == str(t))
