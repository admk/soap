#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


__author__ = 'Xitong Gao'
__email__ = 'xtg08@ic.ac.uk'


_OPERATORS = ['+', '*']


def _parse_r(s):
    s = s.strip()
    bracket_level = 0
    operator_pos = -1
    for i, v in enumerate(s):
        if v == '(':
            bracket_level += 1
        if v == ')':
            bracket_level -= 1
        if bracket_level == 1 and v in _OPERATORS:
            operator_pos = i
            break
    if operator_pos == -1:
        return s
    return (s[operator_pos],
            _parse_r(s[1:operator_pos].strip()),
            _parse_r(s[operator_pos + 1:-1].strip()))


def _unparse_r(t):
    if type(t) is str:
        return t
    if type(t) is not tuple:
        return str(t)
    operator, arg1, arg2 = t
    return '(' + _unparse_r(arg1) + operator + _unparse_r(arg2) + ')'


class ExprParser(object):

    def __init__(self, string_or_tree):
        super(ExprParser, self).__init__()
        if type(string_or_tree) is str:
            self.string = string_or_tree
        elif type(string_or_tree) is tuple:
            self.tree = string_or_tree

    @property
    def tree(self):
        return self._t

    @tree.setter
    def tree(self, t):
        self._t = t
        self._s = _unparse_r(t)

    @property
    def string(self):
        return self._s

    @string.setter
    def string(self, s):
        self._s = s
        self._t = _parse_r(self._s)

    def __str__(self):
        return self.string


if __name__ == '__main__':
    print ExprParser('((a + b) + c)').tree
