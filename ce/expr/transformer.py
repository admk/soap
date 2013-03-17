#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


import re
import sys
import multiprocessing
import random
import functools
from functools import reduce

from ..common import DynamicMethods
from ..semantics import mpq_type

from . import common
from .common import is_exact, is_expr
from .parser import Expr


__author__ = 'Xitong Gao'
__email__ = 'xtg08@ic.ac.uk'


def is_num(v):
    return isinstance(v, (int, long, float))

def is_expr(e):
    return isinstance(e, Expr)


def item_to_list(f):
    return functools.wraps(f)(lambda t: [f(t)])


def none_to_list(f):
    def wrapper(t):
        v = f(t)
        return v if not v is None else []
    return functools.wraps(f)(wrapper)


class ValidationError(Exception):
    """Failed to find equivalence."""


class TreeTransformer(object):

    def __init__(self, tree, validate=False, print_progress=False):
        super(TreeTransformer, self).__init__()
        self._t = tree
        self._v = validate
        self._p = print_progress

    def reduction_methods(self):
        raise NotImplementedError

    def transform_methods(self):
        raise NotImplementedError

    def _closure_r(self, trees, reduced=False):
        v = self._validate if self._v else None
        prev_trees = None
        i = 0
        while trees != prev_trees:
            # print set size
            i += 1
            if self._p:
                if not reduced:
                    sys.stdout.write('\rIteration: %d, Trees: %d' %
                            (i, len(trees)))
                else:
                    sys.stdout.write('\rReduction: %d, Trees: %d' %
                            (i, len(trees)))
                sys.stdout.flush()
            # iterative transition
            prev_trees = trees
            if not reduced:
                for f in self.transform_methods():
                    trees = _step(trees, f, v, True)
                trees = self._closure_r(trees, True)
            else:
                for f in self.reduction_methods():
                    trees = _step(trees, f, v, False)
        return trees

    def closure(self):
        """Perform transforms until transitive closure is reached.

        Returns:
            A set of trees after transform.
        """
        s = self._closure_r([self._t])
        if self._p:
            print('Finished finding closure.')
            print('Reducing commutatively equivalent expressions.')
        # reduce commutatively equivalent expressions
        # FIXME complexity, try hashing instead
        l = set()
        n = len(s)
        for i, e in enumerate(s):
            if self._p:
                sys.stdout.write('\r%d/%d' % (i, n))
                sys.stdout.flush()
            has = False
            for f in l:
                if e.equiv(f):
                    has = True
            if not has:
                l.add(e)
        return l

    def validate(self, t, tn):
        """Perform validation of tree.

        Args:
            t: An original tree.
            tn: A transformed tree.

        Raises:
            ValidationError: If failed to find equivalences between t and tn.
        """
        pass

    def _validate(self, t, tn):
        if t == tn:
            return
        if self._v:
            self.validate(t, tn)


@none_to_list
def associativity(t):
    s = []
    if not t.op in common.ASSOCIATIVITY_OPERATORS:
        return
    if is_expr(t.a1):
        if t.a1.op == t.op:
            s.append(Expr(op=t.op, a1=t.a1.a1,
                          a2=Expr(op=t.op, a1=t.a1.a2, a2=t.a2)))
    if is_expr(t.a2):
        if t.a2.op == t.op:
            s.append(Expr(op=t.op, a1=Expr(op=t.op, a1=t.a1, a2=t.a2.a1),
                          a2=t.a2.a2))
    return s


def distribute_for_distributivity(t):
    s = []
    if t.op in common.LEFT_DISTRIBUTIVITY_OPERATORS and is_expr(t.a2):
        if (t.op, t.a2.op) in common.LEFT_DISTRIBUTIVITY_OPERATOR_PAIRS:
            s.append(
                Expr(op=t.a2.op,
                     a1=Expr(op=t.op, a1=t.a1, a2=t.a2.a1),
                     a2=Expr(op=t.op, a1=t.a1, a2=t.a2.a2)))
    if t.op in common.RIGHT_DISTRIBUTIVITY_OPERATORS and is_expr(t.a1):
        if (t.op, t.a1.op) in common.LEFT_DISTRIBUTIVITY_OPERATOR_PAIRS:
            s.append(
                Expr(op=t.a1.op,
                     a1=Expr(op=t.op, a1=t.a1.a1, a2=t.a2),
                     a2=Expr(op=t.op, a1=t.a1.a2, a2=t.a2)))
    return s


@none_to_list
def collect_for_distributivity(t):
    op, a1, a2 = t
    if not op in (common.LEFT_DISTRIBUTION_OVER_OPERATORS +
                  common.RIGHT_DISTRIBUTION_OVER_OPERATORS):
        return
    # depth test
    if not is_expr(a1) and not is_expr(a2):
        return
    # expand by adding identities
    if is_expr(a2):
        op2, a21, a22 = a2
        if op2 == common.MULTIPLY_OP:
            if a21 == a1:
                a1 = Expr(op=op2, a1=a1, a2=1)
            elif a22 == a1:
                a1 = Expr(op=op2, a1=1, a2=a1)
    if is_expr(a1):
        op1, a11, a12 = a1
        if op1 == common.MULTIPLY_OP:
            if a11 == a2:
                a2 = Expr(op=op1, a1=a2, a2=1)
            elif a12 == a2:
                a1 = Expr(op=op1, a1=1, a2=a2)
    # must be all expressions
    if not is_expr(a1) or not is_expr(a2):
        return
    # equivalences
    op1, a11, a12 = a1
    op2, a21, a22 = a2
    if op1 != op2:
        return
    s = []
    if (op1, op) in common.LEFT_DISTRIBUTIVITY_OPERATOR_PAIRS:
        if a11 == a21:
            s.append(Expr(op=op1, a1=a11, a2=Expr(op=op, a1=a12, a2=a22)))
    if (op2, op) in common.RIGHT_DISTRIBUTIVITY_OPERATOR_PAIRS:
        if a12 == a22:
            s.append(Expr(op=op2, a1=Expr(op=op, a1=a11, a2=a21), a2=a12))
    return s


@none_to_list
def commutativity(t):
    if not t.op in common.COMMUTATIVITY_OPERATORS:
        return
    return [Expr(op=t.op, a1=t.a2, a2=t.a1)]


def _identity_reduction(t, iop, i):
    if t.op != iop:
        return t
    if t.a1 == i:
        return t.a2
    if t.a2 == i:
        return t.a1
    return t


@item_to_list
def multiplicative_identity_reduction(t):
    return _identity_reduction(t, common.MULTIPLY_OP, 1)


@item_to_list
def additive_identity_reduction(t):
    return _identity_reduction(t, common.ADD_OP, 0)


@item_to_list
def zero_reduction(t):
    if t.op != common.MULTIPLY_OP:
        return t
    if t.a1 != 0 and t.a2 != 0:
        return t
    return 0


@item_to_list
def constant_reduction(t):
    if not is_exact(t.a1) or not is_exact(t.a2):
        return t
    if t.op == common.MULTIPLY_OP:
        return t.a1 * t.a2
    if t.op == common.ADD_OP:
        return t.a1 + t.a2


class ExprTreeTransformer(TreeTransformer):

    def __init__(self, *args, **kwargs):
        super(ExprTreeTransformer, self).__init__(*args, **kwargs)

    def transform_methods(self):
        return [associativity, distribute_for_distributivity,
                collect_for_distributivity, commutativity]

    def reduction_methods(self):
        return [multiplicative_identity_reduction,
                additive_identity_reduction, zero_reduction,
                constant_reduction]

    VAR_RE = re.compile(r"[^\d\W]\w*", re.UNICODE)

    def validate(t, tn):
        # FIXME: broken after ErrorSemantics
        def vars(tree_str):
            return set(ExprTreeTransformer.VAR_RE.findall(tree_str))
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


def tuplify_args(f):
    def wrapper(t):
        return f(*t)
    return functools.wraps(f)(wrapper)


def _walk(a):
    return _walk_r(*a)


def _walk_r(t, f, v, c):
    s = {t}
    if not is_expr(t):
        return s
    for e in f(t):
        s.add(e)
    for e in _walk_r(t.a1, f, v, c):
        s.add(Expr(op=t.op, a1=e, a2=t.a2))
    for e in _walk_r(t.a2, f, v, c):
        s.add(Expr(op=t.op, a1=t.a1, a2=e))
    if not c and len(s) > 1 and t in s:
        # there is more than 1 transformed result. discard the
        # original, because the original is transformed to become
        # something else
        s.remove(t)
    if not v:
        return s
    try:
        for tn in s:
            v(t, tn)
    except ValidationError:
        print('Violating transformation:', f.__name__)
        raise
    return s


_pool = multiprocessing.Pool()


def _step(s, f, v=None, closure=False):
    """Find the set of trees related by the function f.
    Arg:
        s: A set of trees.
        f: A function which transforms the trees. It has one argument,
            the tree, and returns a set of trees after transform.
        v: A function which validates the transform.
        closure: If set, it will include everything in self.trees.

    Returns:
        A set of trees related by f.
    """
    chunksize = int(len(s) / multiprocessing.cpu_count()) + 1
    r = _pool.imap(_walk,
        [(t, f, v, closure) for t in s], chunksize)
    return reduce(lambda x, y: x | y, r)


if __name__ == '__main__':
    e = '((a + 2) * (a + 3))'
    t = Expr(e)
    print('Expr:', e)
    print('Tree:', t.tree())
    s = ExprTreeTransformer(t, print_progress=True).closure()
    for n in s:
        print('>', n)
    print('Validating...')
    t = random.sample(s, 1)[0]
    print('Sample Expr:', t)
    r = ExprTreeTransformer(t, print_progress=True).closure()
    if s >= r:
        print('Validated.')
    else:
        print('Inconsistent closure generated.')
