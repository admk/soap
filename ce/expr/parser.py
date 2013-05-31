import ast

from ce.common import ignored
from ce.semantics import mpq
from ce.expr.common import ADD_OP, MULTIPLY_OP, BARRIER_OP


def try_to_number(s):
    try:
        return mpq(s)
    except (ValueError, TypeError):
        return s


OPERATOR_MAP = {
    ast.Add: ADD_OP,
    ast.Mult: MULTIPLY_OP,
    ast.BitOr: BARRIER_OP,
}


class ParserSyntaxError(SyntaxError):
    pass


def parse(s, cls):
    def _parse_r(t):
        with ignored(AttributeError):
            return t.n
        with ignored(AttributeError):
            return t.id
        with ignored(AttributeError):
            return tuple(_parse_r(v) for v in t.elts)
        try:
            op = OPERATOR_MAP[t.op.__class__]
            a1 = _parse_r(t.left)
            a2 = _parse_r(t.right)
            return cls(op, a1, a2)
        except KeyError:
            raise ParserSyntaxError(
                'Unrecognised binary operator %s' % str(t.op))
        except AttributeError:
            raise ParserSyntaxError('Unknown token %s' % str(t))
    try:
        body = ast.parse(s.replace('\n', '').strip(), mode='eval').body
        return _parse_r(body)
    except (TypeError, AttributeError):
        raise TypeError('Parse argument must be a string')
    except SyntaxError as e:
        raise ParserSyntaxError(e)


if __name__ == '__main__':
    print(parse('a + b * c + d'))
