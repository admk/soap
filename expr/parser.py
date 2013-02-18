#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


from common import OPERATORS


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
    arg1 = _parse_r(s[1:operator_pos].strip())
    arg2 = _parse_r(s[operator_pos + 1:-1].strip())
    return Expr(string=None, op=s[operator_pos], arg1=arg1, arg2=arg2)


class Expr(object):

    def __init__(self, string=None, op=None, arg1=None, arg2=None):
        super(Expr, self).__init__()
        if string:
            expr = _parse_r(string)
            self.op = expr.op
            self.arg1 = expr.arg1
            self.arg2 = expr.arg2
        else:
            self.op = op
            self.arg1 = _try_to_number(arg1)
            self.arg2 = _try_to_number(arg2)

    def tuple(self):
        def to_tuple(a):
            if isinstance(a, Expr):
                return a.tuple()
            return a
        return (self.op, to_tuple(self.arg1), to_tuple(self.arg2))

    def __str__(self):
        return '(%s %s %s)' % (str(self.arg1), self.op, str(self.arg2))

    def __repr__(self):
        return "Expr(op='%s', arg1=%s, arg2=%s)" % \
                (self.op, repr(self.arg1), repr(self.arg2))

    def __eq__(self, other):
        if not isinstance(other, Expr):
            return False
        return self.tuple() == other.tuple()

    def __hash__(self):
        return hash(self.tuple())


if __name__ == '__main__':
    s = '((a + 1) * c)'
    t = repr(Expr(s))
    print t
    t = eval(t)
    assert(s == str(t))
