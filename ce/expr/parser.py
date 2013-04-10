#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


from ..semantics import mpq
from .common import OPERATORS, ADD_OP, MULTIPLY_OP


def try_to_number(s):
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
    return Expr(s[operator_pos], a1, a2)
