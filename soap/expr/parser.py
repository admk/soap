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


def raise_parser_error(desc, text, token):
    exc = ParserSyntaxError(str(desc))
    exc.text = text
    exc.lineno = token.lineno
    exc.offset = token.col_offset
    raise exc


def ast_to_expr(t, cls, s):
    with ignored(AttributeError):
        return t.n
    with ignored(AttributeError):
        return t.id
    with ignored(AttributeError):
        return t.s
    with ignored(AttributeError):
        return tuple(ast_to_expr(v, cls, s) for v in t.elts)
    try:
        op = OPERATOR_MAP[t.op.__class__]
        if op == UNARY_SUBTRACT_OP:
            return -ast_to_expr(t.operand, cls, s)
        a1 = ast_to_expr(t.left, cls, s)
        a2 = ast_to_expr(t.right, cls, s)
        if op == DIVIDE_OP:
            try:
                return gmpy2.mpq(a1, a2)
            except TypeError:
                pass
        return cls(op, a1, a2)
    except KeyError:
        raise_parser_error('Unrecognised operator %s' % str(t.op), s, t)
    except AttributeError:
        raise_parser_error('Unknown token %s' % str(t), s, t)


def parse(s, cls):
    """Parses a string into an instance of class `cls`.

    :param s: a string with valid syntax.
    :type s: str
    :param cls: the class of the expression.
    :type cls: types.ClassType
    """
    s = s.replace('\n', '').strip()
    try:
        body = ast.parse(s, mode='eval').body
        return ast_to_expr(body, cls, s)
    except (TypeError, AttributeError):
        raise TypeError('Parse argument must be a string')
    except SyntaxError as e:
        if type(e) is not ParserSyntaxError:
            raise ParserSyntaxError(e)
        raise e
