import itertools
import gmpy2

from ce.common import ignored


def precisions():
    import ce.semantics.flopoco as flopoco
    return flopoco.wf_range


def precision_context(prec):
    return gmpy2.local_context(gmpy2.ieee(128), precision=prec)


def set_precision_recursive(expr, prec):
    from ce.expr import BARRIER_OP
    if expr.op != BARRIER_OP:
        expr.prec = prec
    for a in expr.args:
        with ignored(ValueError, AttributeError):
            set_precision_recursive(a, prec)


def precision_permutations(expr, permutations=precisions()):
    from ce.expr import Expr, BARRIER_OP
    try:
        p1, p2 = [precision_permutations(a, permutations) for a in expr.args]
        if expr.op == BARRIER_OP:
            permutations = [None]
        elif not expr.prec is None:
            permutations = [expr.prec]
        return [Expr(expr.op, a1, a2, prec=p)
                for p in permutations for a1, a2 in itertools.product(p1, p2)]
    except AttributeError:
        return [expr]
