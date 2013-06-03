import itertools
import gmpy2

import ce.logger as logger
from ce.common import ignored
from ce.precision.common import PRECISIONS


def precision_context(prec):
    prec += 1
    return gmpy2.local_context(gmpy2.ieee(128), precision=prec)


def set_precision_recursive(expr, prec):
    from ce.expr import BARRIER_OP
    if expr.op != BARRIER_OP:
        expr.prec = prec
    for a in expr.args:
        with ignored(ValueError, AttributeError):
            set_precision_recursive(a, prec)


def precision_permutations(expr, prec_list=PRECISIONS):
    from ce.expr import Expr, BARRIER_OP, is_expr
    if not is_expr(expr):
        s = []
        for e in expr:
            s += precision_permutations(e, prec_list)
        return s
    try:
        p1, p2 = [precision_permutations(a, prec_list) for a in expr.args]
        if expr.op == BARRIER_OP:
            prec_list = [None]
        elif not expr.prec is None:
            prec_list = [expr.prec]
        s = []
        n = len(p1) * len(p2) * len(prec_list)
        i = 0
        for a1, a2 in itertools.product(p1, p2):
            for p in prec_list:
                i += 1
                logger.persistent('Permutation', '%d/%d' % (i, n),
                                  l=logger.levels.debug)
                s.append(Expr(expr.op, a1, a2, prec=p))
        logger.unpersistent('Permutation')
        return s
    except AttributeError:
        return [expr]


def precision_variations(expr_or_set, prec_list=PRECISIONS):
    from ce.expr import Expr, is_expr
    if is_expr(expr_or_set):
        return [Expr(expr_or_set, prec=p) for p in prec_list]
    s = []
    for e in expr_or_set:
        s += precision_variations(e, prec_list)
    return s
