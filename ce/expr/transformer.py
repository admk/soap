#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


import re
import sys
import multiprocessing
import random
import functools

from . import common
from .common import cached, is_exact, is_expr
from .parser import Expr


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
        self._t = tree
        self._v = validate
        self._p = print_progress
        super().__init__()

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
            if self._p:
                i += 1
                sys.stdout.write(
                    '\r%s: %d, Trees: %d.' %
                    ('Reduction' if reduced else 'Iteration',
                     i, len(trees)))
                sys.stdout.flush()
            # iterative transition
            prev_trees = trees
            if not reduced:
                trees = _step(trees, self.transform_methods(), v, True)
                trees = self._closure_r(trees, True)
            else:
                trees = _step(trees, self.reduction_methods(), v, False)
        return trees

    def closure(self):
        """Perform transforms until transitive closure is reached.

        Returns:
            A set of trees after transform.
        """
        s = self._closure_r([self._t])
        if self._p:
            print('Finished finding closure.')
        return s

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
    def expr_from_args(args):
        for a in args:
            al = list(args)
            al.remove(a)
            yield Expr(t.op, a, Expr(t.op, al))
    if not t.op in common.ASSOCIATIVITY_OPERATORS:
        return
    s = []
    if is_expr(t.a1) and t.a1.op == t.op:
        s.extend(list(expr_from_args(t.a1.args + [t.a2])))
    if is_expr(t.a2) and t.a2.op == t.op:
        s.extend(list(expr_from_args(t.a2.args + [t.a1])))
    return s


def distribute_for_distributivity(t):
    s = []
    if t.op in common.LEFT_DISTRIBUTIVITY_OPERATORS and is_expr(t.a2):
        if (t.op, t.a2.op) in common.LEFT_DISTRIBUTIVITY_OPERATOR_PAIRS:
            s.append(Expr(t.a2.op,
                          Expr(t.op, t.a1, t.a2.a1),
                          Expr(t.op, t.a1, t.a2.a2)))
    if t.op in common.RIGHT_DISTRIBUTIVITY_OPERATORS and is_expr(t.a1):
        if (t.op, t.a1.op) in common.RIGHT_DISTRIBUTIVITY_OPERATOR_PAIRS:
            s.append(Expr(t.a1.op,
                          Expr(t.op, t.a1.a1, t.a2),
                          Expr(t.op, t.a1.a2, t.a2)))
    return s


@none_to_list
def collect_for_distributivity(t):

    def al(a):
        if not is_expr(a):
            return [a, 1]
        if (a.op, t.op) == (common.MULTIPLY_OP, common.ADD_OP):
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
    if t.op != common.ADD_OP:
        return
    if all(is_expr(a) and a.op != common.MULTIPLY_OP for a in t.args):
        return
    # forming list
    af = [al(arg) for arg in t.args]
    # find common elements
    s = []
    for ac in functools.reduce(lambda x, y: set(x) & set(y), af):
        an = [sub(an, ac) for an in af]
        s.append(Expr(common.MULTIPLY_OP, ac, Expr(common.ADD_OP, an)))
    return s


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
        super().__init__(*args, **kwargs)

    def transform_methods(self):
        return [associativity, distribute_for_distributivity,
                collect_for_distributivity]

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


@cached
def _walk_r(t, f, v, c):
    s = {t}
    if not is_expr(t):
        return s
    for e in f(t):
        s.add(e)
    for e in _walk_r(t.a1, f, v, c):
        s.add(Expr(t.op, e, t.a2))
    for e in _walk_r(t.a2, f, v, c):
        s.add(Expr(t.op, t.a1, e))
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


def par_union(sl):
    return functools.reduce(lambda s, t: s | t, sl)


_pool = multiprocessing.Pool()


def _iunion(sl, no_processes):
    def chunks(l, n):
        for i in range(0, len(l), n):
            yield l[i:i+n]
    chunksize = int(len(sl) / no_processes) + 2
    while len(sl) > 1:
        sys.stdout.write('\rUnion: %d.' % len(sl))
        sys.stdout.flush()
        sl = list(_pool.imap_unordered(par_union, chunks(sl, chunksize)))
    return sl.pop()


def _step(s, fs, v=None, c=False, m=True):
    """Find the set of trees related by the function f.

    Args:
        s: A set of trees.
        fs: A set of functions which transforms the trees. Each function has
            one argument, the tree, and returns a set of trees after transform.
        v: A function which validates the transform.
        c: If set, it will include everything in s. Otherwise only derived
            trees.

    Returns:
        A set of trees related by f.
    """
    if m:
        cpu_count = multiprocessing.cpu_count()
        chunksize = int(len(s) / cpu_count) + 1
        map = _pool.imap_unordered
        union = _iunion
    else:
        cpu_count = chunksize = 1
        map = lambda f, l, _: [f(a) for a in l]
        union = lambda s, _: functools.reduce(lambda x, y: x | y, s)
    for f in fs:
        s = [(t, f, v, c) for i, t in enumerate(s)]
        s = list(map(_walk, s, chunksize))
        s = union(s, cpu_count)
    return s


if __name__ == '__main__':
    profile = False
    memory_profile = True
    if profile:
        import pycallgraph
        pycallgraph.start_trace()
    if memory_profile:
        import objgraph
        objgraph.show_growth()
    from datetime import datetime
    startTime = datetime.now()
    e = '(((a + b) * (a + b)) * a)'
    t = Expr(e)
    print('Expr:', e)
    print('Tree:', t.tree())
    s = ExprTreeTransformer(t, print_progress=True).closure()
    print(datetime.now() - startTime)
    if memory_profile:
        objgraph.show_growth()
    if profile:
        pycallgraph.make_dot_graph('test.png')
