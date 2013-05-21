import ast

from ce.semantics import mpq, cast_error
from ce.expr.common import ADD_OP, MULTIPLY_OP


def try_to_number(s):
    try:
        return mpq(s)
    except (ValueError, TypeError):
        return s


OPERATOR_MAP = {
    ast.Add: ADD_OP,
    ast.Mult: MULTIPLY_OP,
}


def parse(s, cls):
    def _parse_r(t):
        try:
            return t.n
        except AttributeError:
            pass
        try:
            return t.id
        except AttributeError:
            pass
        try:
            op = OPERATOR_MAP[t.op.__class__]
            a1 = _parse_r(t.left)
            a2 = _parse_r(t.right)
            return cls(op, a1, a2)
        except AttributeError:
            pass
        try:
            bounds = [_parse_r(v) for v in t.elts]
            return cast_error(*bounds)
        except AttributeError:
            raise SyntaxError('Unknown token %s' % str(t))
        except KeyError:
            raise SyntaxError('Unrecognised binary operator %s' % str(t.op))
    try:
        body = ast.parse(s, mode='eval').body
    except TypeError:
        raise TypeError('Parse argument must be a string')
    return _parse_r(body)


if __name__ == '__main__':
    print(parse('a + b * c + d'))
