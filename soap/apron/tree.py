from tempfile import TemporaryFile

from soap.apron.ffi import library, encode_str
from soap.common import base_dispatcher
from soap.expression import operators
from soap.semantics import is_constant, Interval, mpfr_type, mpq, mpz_type


class ApronTree(object):
    def __init__(self, expr):
        super().__init__()
        self._expr = expr

    def __str__(self):
        with TemporaryFile() as out:
            library.ap_texpr1_fprint(out, self._expr)
            out.seek(0)
            return out.read().decode('utf-8')

    def __repr__(self):
        return '{}(<cffi: {}>)'.format(self.__class__.__name__, self.__str__())

    def __del__(self):
        library.ap_texpr1_free(self._expr)


_operator_map = {
    operators.ADD_OP: library.AP_TEXPR_ADD,
    operators.SUBTRACT_OP: library.AP_TEXPR_SUB,
    operators.MULTIPLY_OP: library.AP_TEXPR_MUL,
    operators.DIVIDE_OP: library.AP_TEXPR_DIV,
    operators.UNARY_SUBTRACT_OP: library.AP_TEXPR_NEG,
}


class ApronTreeGenerator(base_dispatcher('generate')):
    def generic_generate(self, expr, env, state):
        raise TypeError('Do not know how to generate {!r}'.format(expr))

    def generate_numeral(self, expr, env, state):
        if not is_constant(expr):
            raise TypeError('Numerical value must be constant.')
        if isinstance(expr, Interval):
            expr = expr.min
        if isinstance(expr, (float, mpfr_type)):
            expr = mpq(expr)
            expr = library.ap_texpr1_cst_scalar_frac(
                env, expr.numerator, expr.denominator)
        if isinstance(expr, (int, mpz_type)):
            expr = int(expr)
            expr = library.ap_texpr1_cst_scalar_int(env, expr)
        return expr

    def generate_Variable(self, expr, env, state):
        return library.ap_texpr1_var(env, encode_str(expr.name))

    def generate_UnaryArithExpr(self, expr, env, state):
        op = _operator_map[expr.op]
        arg = self(expr.a, env, state)
        return library.ap_texpr1_unop(
            op, arg, library.AP_RTYPE_REAL, library.AP_RDIR_NEAREST)

    def generate_BinaryArithExpr(self, expr, env, state):
        op = _operator_map[expr.op]
        a1, a2 = [self(a, env, state) for a in expr.args]
        return library.ap_texpr1_binop(
            op, a1, a2, library.AP_RTYPE_REAL, library.AP_RDIR_NEAREST)


def apron_tree(expr, env):
    env = env._environment
    generator = ApronTreeGenerator()
    return ApronTree(generator(expr, env, None))
