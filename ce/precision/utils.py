import gmpy2

from ce.common import ignored


def precision_context(prec):
    return gmpy2.local_context(gmpy2.ieee(128), precision=prec)


def set_precision_recursive(expr, prec):
    expr.prec = prec
    for a in expr.args:
        with ignored(ValueError, AttributeError):
            set_precision_recursive(a, prec)
