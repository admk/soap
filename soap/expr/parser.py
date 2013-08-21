"""
.. module:: soap.expr.parser
    :synopsis: Parser for class:`soap.expr.Expr`.
"""
import ast
import gmpy2

from soap.common import ignored
from soap.semantics import mpq
from soap.expr.common import (
    ADD_OP, MULTIPLY_OP, DIVIDE_OP, BARRIER_OP, UNARY_SUBTRACT_OP
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
}


class ParserSyntaxError(SyntaxError):
    """Syntax Error Exception for :func:`parse`."""


def parse(s, cls):
    """Parses a string into an instance of class `cls`.

    :param s: a string with valid syntax.
    :type s: str
    :param cls: the class of the expression.
    :type cls: types.ClassType
    """
    def _parse_r(t):
        with ignored(AttributeError):
            return t.n
        with ignored(AttributeError):
            return t.id
        with ignored(AttributeError):
            return t.s
        with ignored(AttributeError):
            return tuple(_parse_r(v) for v in t.elts)
        try:
            op = OPERATOR_MAP[t.op.__class__]
            if op == UNARY_SUBTRACT_OP:
                return -_parse_r(t.operand)
            a1 = _parse_r(t.left)
            a2 = _parse_r(t.right)
            if op == DIVIDE_OP:
                try:
                    return gmpy2.mpq(a1, a2)
                except TypeError:
                    pass
            return cls(op, a1, a2)
        except KeyError:
            raise ParserSyntaxError('Unrecognised operator %s' % str(t.op))
        except AttributeError:
            raise ParserSyntaxError('Unknown token %s' % str(t))
    try:
        body = ast.parse(s.replace('\n', '').strip(), mode='eval').body
        return _parse_r(body)
    except (TypeError, AttributeError):
        raise TypeError('Parse argument must be a string')
    except SyntaxError as e:
        raise ParserSyntaxError(e)
