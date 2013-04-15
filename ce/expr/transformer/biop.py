import re
import random

from ce.expr.common import ADD_OP, MULTIPLY_OP, ASSOCIATIVITY_OPERATORS, \
    LEFT_DISTRIBUTIVITY_OPERATORS, LEFT_DISTRIBUTIVITY_OPERATOR_PAIRS, \
    RIGHT_DISTRIBUTIVITY_OPERATORS, RIGHT_DISTRIBUTIVITY_OPERATOR_PAIRS
import ce.logger as logger
from ..common import is_exact, is_expr
from ..biop import Expr
from .core import item_to_list, none_to_list, TreeTransformer, ValidationError


@none_to_list
def associativity(t):
    def expr_from_args(args):
        for a in args:
            al = list(args)
            al.remove(a)
            yield Expr(t.op, a, Expr(t.op, al))
    if not t.op in ASSOCIATIVITY_OPERATORS:
        return
    s = []
    if is_expr(t.a1) and t.a1.op == t.op:
        s.extend(list(expr_from_args(t.a1.args + [t.a2])))
    if is_expr(t.a2) and t.a2.op == t.op:
        s.extend(list(expr_from_args(t.a2.args + [t.a1])))
    return s


def distribute_for_distributivity(t):
    s = []
    if t.op in LEFT_DISTRIBUTIVITY_OPERATORS and is_expr(t.a2):
        if (t.op, t.a2.op) in LEFT_DISTRIBUTIVITY_OPERATOR_PAIRS:
            s.append(Expr(t.a2.op,
                          Expr(t.op, t.a1, t.a2.a1),
                          Expr(t.op, t.a1, t.a2.a2)))
    if t.op in RIGHT_DISTRIBUTIVITY_OPERATORS and is_expr(t.a1):
        if (t.op, t.a1.op) in RIGHT_DISTRIBUTIVITY_OPERATOR_PAIRS:
            s.append(Expr(t.a1.op,
                          Expr(t.op, t.a1.a1, t.a2),
                          Expr(t.op, t.a1.a2, t.a2)))
    return s


@none_to_list
def collect_for_distributivity(t):

    def al(a):
        if not is_expr(a):
            return [a, 1]
        if (a.op, t.op) == (MULTIPLY_OP, ADD_OP):
            return a.args
        return [a, 1]

    def sub(l, e):
        l = list(l)
        l.remove(e)
        return l.pop()

    # depth test
    if all(not is_expr(a) for a in t.args):
        return
    # operator tests
    if t.op != ADD_OP:
        return
    if all(a.op != MULTIPLY_OP for a in t.args if is_expr(a)):
        return
    # forming list
    af = [al(arg) for arg in t.args]
    # find common elements
    s = []
    for ac in set.intersection(*(set(a) for a in af)):
        an = [sub(an, ac) for an in af]
        s.append(Expr(MULTIPLY_OP, ac, Expr(ADD_OP, an)))
    return s


def _identity_reduction(t, iop, i):
    if t.op != iop:
        return
    if t.a1 == i:
        return t.a2
    if t.a2 == i:
        return t.a1


@item_to_list
def multiplicative_identity_reduction(t):
    return _identity_reduction(t, MULTIPLY_OP, 1)


@item_to_list
def additive_identity_reduction(t):
    return _identity_reduction(t, ADD_OP, 0)


@item_to_list
def zero_reduction(t):
    if t.op != MULTIPLY_OP:
        return
    if t.a1 != 0 and t.a2 != 0:
        return
    return 0


@item_to_list
def constant_reduction(t):
    if not is_exact(t.a1) or not is_exact(t.a2):
        return
    if t.op == MULTIPLY_OP:
        return t.a1 * t.a2
    if t.op == ADD_OP:
        return t.a1 + t.a2


class BiOpTreeTransformer(TreeTransformer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    transform_methods = [associativity,
                         distribute_for_distributivity,
                         collect_for_distributivity]

    reduction_methods = [multiplicative_identity_reduction,
                         additive_identity_reduction, zero_reduction,
                         constant_reduction]

    VAR_RE = re.compile(r"[^\d\W]\w*", re.UNICODE)

    def validate(t, tn):
        # FIXME: broken after ErrorSemantics
        def vars(tree_str):
            return set(BiOpTreeTransformer.VAR_RE.findall(tree_str))
        to, no = ts, ns = str(t), str(tn)
        tsv, nsv = vars(ts), vars(ns)
        if tsv != nsv:
            raise ValidationError('Variable domain mismatch.')
        vv = {v: random.randint(0, 127) for v in tsv}
        for v, i in vv.items():
            ts = re.sub(r'\b%s\b' % v, str(i), ts)
            ns = re.sub(r'\b%s\b' % v, str(i), ns)
        if eval(ts) != eval(ns):
            raise ValidationError(
                'Failed validation\n'
                'Original: %s %s,\n'
                'Transformed: %s %s' % (to, t, no, tn))


if __name__ == '__main__':
    profile = False
    memory_profile = True
    logger.set_context(level=logger.levels.debug)
    if profile:
        import pycallgraph
        pycallgraph.start_trace()
    from datetime import datetime
    startTime = datetime.now()
    e = '(a + 1) * (a + 1) * a'
    t = Expr(e)
    logger.debug('Expr:', str(t))
    logger.debug('Tree:', t.tree())
    if memory_profile:
        from pympler.classtracker import ClassTracker
        from ce.expr.common import Flyweight, _cache_map
        tracker = ClassTracker()
        tracker.track_object(Flyweight._cache)
        tracker.track_class(Expr)
    s = BiOpTreeTransformer(t).closure()
    logger.debug(datetime.now() - startTime)
    logger.debug(len(s))
    if memory_profile:
        from pympler.asizeof import asizeof
        tracker.track_object(s)
        tracker.create_snapshot()
        tracker.stats.print_summary()
        print(asizeof(Flyweight._cache))
        print(asizeof(_cache_map))
    if profile:
        pycallgraph.make_dot_graph('test.png')
