"""
.. module:: soap.transformer.arith
    :synopsis: Transforms arithmetic expression instances.
"""
import re
import random

import soap.logger as logger
from soap.expression.common import (
    ADD_OP, MULTIPLY_OP, ASSOCIATIVITY_OPERATORS,
    LEFT_DISTRIBUTIVITY_OPERATORS, LEFT_DISTRIBUTIVITY_OPERATOR_PAIRS,
    RIGHT_DISTRIBUTIVITY_OPERATORS, RIGHT_DISTRIBUTIVITY_OPERATOR_PAIRS,
    is_expr
)
from soap.expression import Expr
from soap.transformer.core import (
    item_to_list, none_to_list, TreeTransformer, ValidationError
)
from soap.semantics import mpq_type


@none_to_list
def associativity(t):
    """Associativity relation between expressions.

    For example:
        (a + b) + c == a + (b + c)

    :param t: The expression tree.
    :type t: :class:`soap.expression.Expr`
    :returns: A list of expressions that are derived with assoicativity from
        the input tree.
    """
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
    """Distributivity relation between expressions by distributing.

    For example:
        (a + b) * c == (a * c) + (b * c)

    :param t: The expression tree.
    :type t: :class:`soap.expression.Expr`
    :returns: A list of expressions that are derived with distributivity from
        the input tree.
    """
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
    """Distributivity relation between expressions by collecting common terms.

    For example:
        (a * c) + (b * c) == (a + b) * c

    :param t: The expression tree.
    :type t: :class:`soap.expression.Expr`
    :returns: A list of expressions that are derived with distributivity from
        the input tree.
    """
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
    """Multiplicative identity relation from an expression.

    For example:
        a * 1 == a

    :param t: The expression tree.
    :type t: :class:`soap.expression.Expr`
    :returns: A list containing an expression related by this reduction rule.
    """
    return _identity_reduction(t, MULTIPLY_OP, 1)


@item_to_list
def additive_identity_reduction(t):
    """Additive identity relation from an expression.

    For example:
        a + 0 == a

    :param t: The expression tree.
    :type t: :class:`soap.expression.Expr`
    :returns: A list containing an expression related by this reduction rule.
    """
    return _identity_reduction(t, ADD_OP, 0)


@item_to_list
def zero_reduction(t):
    """The zero-property of expressions.

    For example:
        a * 0 == 0

    :param t: The expression tree.
    :type t: :class:`soap.expression.Expr`
    :returns: A list containing an expression related by this reduction rule.
    """
    if t.op != MULTIPLY_OP:
        return
    if t.a1 != 0 and t.a2 != 0:
        return
    return 0


@item_to_list
def constant_reduction(t):
    """Constant propagation.

    For example:
        1 + 2 == 3

    :param t: The expression tree.
    :type t: :class:`soap.expression.Expr`
    :returns: A list containing an expression related by this reduction rule.
    """
    def is_exact(v):
        return isinstance(v, (int, mpq_type))
    if not is_exact(t.a1) or not is_exact(t.a2):
        return
    if t.op == MULTIPLY_OP:
        return t.a1 * t.a2
    if t.op == ADD_OP:
        return t.a1 + t.a2


class ArithTreeTransformer(TreeTransformer):
    """The class that provides transformation of binary operator expressions.

    It has the same arguments as :class:`soap.transformer.TreeTransformer`,
    which is the class it is derived from.
    """
    transform_methods = [associativity,
                         distribute_for_distributivity,
                         collect_for_distributivity]

    reduction_methods = [multiplicative_identity_reduction,
                         additive_identity_reduction, zero_reduction,
                         constant_reduction]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    VAR_RE = re.compile(r"[^\d\W]\w*", re.UNICODE)

    def validate(t, tn):
        # FIXME: broken after ErrorSemantics
        def vars(tree_str):
            return set(ArithTreeTransformer.VAR_RE.findall(tree_str))
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
    from soap.common import profiled, timed
    Expr.__repr__ = Expr.__str__
    logger.set_context(level=logger.levels.info)
    e = '(a + 1) * b | (b + 1) * a | a * b'
    t = Expr(e)
    logger.info('Expr:', str(t))
    logger.info('Tree:', t.tree())
    with profiled(), timed():
        s = ArithTreeTransformer(t).closure()
    logger.info('Transformed:', len(s))
    from soap.analysis.utils import plot, analyse
    v = {'a': ['1', '2'], 'b': ['100', '200']}
    a = analyse(s, v)
    logger.info(a)
    plot(a)
