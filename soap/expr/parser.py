"""
.. module:: soap.expr.parser
    :synopsis: Parser for class:`soap.expr.Expr`.
"""
import ast
import gmpy2

from soap.common import ignored
from soap.semantics import mpq
from soap.expr.common import (
    ADD_OP, MULTIPLY_OP, DIVIDE_OP, BARRIER_OP, UNARY_SUBTRACT_OP,
    EQUAL_OP, GREATER_OP, LESS_OP, UNARY_NEGATION_OP, AND_OP, OR_OP
)


def try_to_number(s):
    try:
        return mpq(s)
    except (ValueError, TypeError):
        return s


OPERATOR_MAP = {
    ast.Add: ADD_OP,
    ast.Mult: MULTIPLY_OP,
    ast.Div: DIVIDE_OP,
    ast.BitOr: BARRIER_OP,
    ast.USub: UNARY_SUBTRACT_OP,
    ast.Eq: EQUAL_OP,
    ast.Gt: GREATER_OP,
    ast.Lt: LESS_OP,
    ast.Not: UNARY_NEGATION_OP,
    ast.And: AND_OP,
    ast.Or: OR_OP,
}


class ParserSyntaxError(SyntaxError):
    """Syntax Error Exception for :func:`parse`."""


def parse(s):
    """Parses a string into an instance of class `cls`.

    :param s: a string with valid syntax.
    :type s: str
    """
    def _parse_r(t):
        from soap.expr.arith import Expr
        from soap.expr.bool import BoolExpr
        with ignored(AttributeError):
            return t.n
        with ignored(AttributeError):
            return t.id
        with ignored(AttributeError):
            return t.s
        with ignored(AttributeError):
            return tuple(_parse_r(v) for v in t.elts)
        with ignored(AttributeError):
            op = OPERATOR_MAP[t.ops.pop().__class__]
            a1 = _parse_r(t.left)
            a2 = _parse_r(t.comparators.pop())
            return BoolExpr(op, a1, a2)
        try:
            op = OPERATOR_MAP[t.op.__class__]
            if op == UNARY_SUBTRACT_OP:
                a1 = _parse_r(t.operand)
                a2 = None
            else:
                a1 = _parse_r(t.left)
                a2 = _parse_r(t.right)
            if op == DIVIDE_OP:
                try:
                    return gmpy2.mpq(a1, a2)
                except TypeError:
                    pass
            return Expr(op, a1, a2)
        except KeyError:
            raise ParserSyntaxError('Unrecognised operator %s' % str(t.op))
        except AttributeError:
            raise ParserSyntaxError('Unknown token %s' % str(t))
    try:
        body = ast.parse(s.replace('\n', '').strip(), mode='eval').body
    except (TypeError, AttributeError):
        raise TypeError('Parse argument must be a string')
    try:
        return _parse_r(body)
    except SyntaxError as e:
        raise ParserSyntaxError(e)
