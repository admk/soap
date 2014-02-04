"""
.. module:: soap.expression.parser
    :synopsis: Parser for class:`soap.expression.Expr`.
"""
import ast

from soap.expression.operators import (
    ADD_OP, SUBTRACT_OP, MULTIPLY_OP, DIVIDE_OP, BARRIER_OP, UNARY_SUBTRACT_OP,
    EQUAL_OP, NOT_EQUAL_OP, GREATER_OP, LESS_OP, GREATER_EQUAL_OP,
    LESS_EQUAL_OP, UNARY_NEGATION_OP, AND_OP, OR_OP, TERNARY_SELECT_OP,
)


OPERATOR_MAP = {
    ast.Add: ADD_OP,
    ast.Sub: SUBTRACT_OP,
    ast.Mult: MULTIPLY_OP,
    ast.Div: DIVIDE_OP,
    ast.BitOr: BARRIER_OP,
    ast.USub: UNARY_SUBTRACT_OP,
    ast.Eq: EQUAL_OP,
    ast.NotEq: NOT_EQUAL_OP,
    ast.Gt: GREATER_OP,
    ast.GtE: GREATER_EQUAL_OP,
    ast.Lt: LESS_OP,
    ast.LtE: LESS_EQUAL_OP,
    ast.Invert: UNARY_NEGATION_OP,
    ast.And: AND_OP,
    ast.Or: OR_OP,
}


class ParserSyntaxError(SyntaxError):
    """Syntax Error Exception for :func:`parse`."""


def raise_parser_error(desc, text, token):
    exc = ParserSyntaxError(str(desc))
    exc.text = text
    exc.lineno = token.lineno
    exc.offset = token.col_offset
    raise exc


def ast_to_expr(t, s):
    from soap.expression.common import expression_factory
    from soap.semantics.error import cast, mpz, mpfr
    if isinstance(t, ast.Num):
        v = t.n
        if isinstance(v, int):
            return mpz(v)
        if isinstance(v, float):
            return mpfr(v)
    if isinstance(t, ast.Name):
        return expression_factory(t.id)
    if isinstance(t, ast.Str):
        return t.s
    if isinstance(t, ast.List):
        t = tuple(ast_to_expr(v, s) for v in t.elts)
        if len(t) == 2:
            t = cast(t)
        return t
    if isinstance(t, ast.Compare):
        op = OPERATOR_MAP[t.ops.pop().__class__]
        a1 = ast_to_expr(t.left, s)
        a2 = ast_to_expr(t.comparators.pop(), s)
        return expression_factory(op, a1, a2)
    if isinstance(t, ast.IfExp):
        args = (ast_to_expr(a, s) for a in (t.test, t.body, t.orelse))
        return expression_factory(TERNARY_SELECT_OP, *args)
    op = OPERATOR_MAP[t.op.__class__]
    if isinstance(t, ast.BoolOp):
        args = (ast_to_expr(a, s) for a in t.values)
        return expression_factory(op, *args)
    if isinstance(t, ast.UnaryOp):
        a = ast_to_expr(t.operand, s)
        return expression_factory(op, a)
    if isinstance(t, ast.BinOp):
        a1 = ast_to_expr(t.left, s)
        a2 = ast_to_expr(t.right, s)
        return expression_factory(op, a1, a2)
    raise_parser_error('Unknown token %s' % t, s, t)


def parse(s):
    """Parses a string into an instance of class `cls`.

    :param s: a string with valid syntax.
    :type s: str
    """
    s = s.replace('\n', '').strip()
    try:
        body = ast.parse(s, mode='eval').body
        return ast_to_expr(body, s)
    except SyntaxError as e:
        if type(e) is not ParserSyntaxError:
            raise ParserSyntaxError(e)
        raise e
