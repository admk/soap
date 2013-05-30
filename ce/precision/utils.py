import gmpy2

from ce.common import ignored


def precision_context(prec):
    return gmpy2.local_context(gmpy2.ieee(128), precision=prec)
