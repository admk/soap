#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


from __future__ import print_function
import re
import sys
import random
import functools

from ..common import DynamicMethods
from common import ADD_OP, MULTIPLY_OP
from parser import Expr


__author__ = 'Xitong Gao'
__email__ = 'xtg08@ic.ac.uk'


def is_num(v):
    return isinstance(v, (int, long, float))


def is_expr(e):
    return isinstance(e, Expr)


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
    return reduce(lambda x, y: x | y, [_walk_r(t, f, v, closure) for t in s])


def _walk_r(t, f, v, c):
    s = set([t])
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


def item_to_list(f):
    return functools.wraps(f)(lambda t: [f(t)])


def none_to_list(f):
    def wrapper(t):
        v = f(t)
        return v if v else []
    return functools.wraps(f)(wrapper)


class ValidationError(Exception):
    """Failed to find equivalence."""


class TreeTransformer(DynamicMethods):

    def __init__(self, tree, validate=False, print_progress=False):
        super(TreeTransformer, self).__init__()
        self._t = tree
        self._v = validate
        self._p = print_progress

    def _closure_r(self, trees, reduced=False):
        v = self._validate if self._v else None
        prev_trees = None
        while trees != prev_trees:
            # print set size
            if self._p:
                sys.stdout.write('%d ' % len(trees))
                sys.stdout.flush()
            # iterative transition
            prev_trees = trees
            if not reduced:
                for f in self._transform_methods():
                    trees = _step(trees, none_to_list(f), v, True)
                trees = self._closure_r(trees, True)
            else:
                for f in self._reduction_methods():
                    trees = _step(trees, item_to_list(f), v, False)
        return trees

    def closure(self):
        """Perform transforms until transitive closure is reached.

        Returns:
            A set of trees after transform.
        """
        return self._closure_r([self._t])

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

    def _reduction_methods(self):
        return self.list_methods(lambda m: m.endswith('reduction'))

    def _transform_methods(self):
        return self.list_methods(lambda m: m.endswith('tivity'))


class ExprTreeTransformer(TreeTransformer):

    def __init__(self, tree, validate=False, print_progress=False):
        super(ExprTreeTransformer, self).__init__(
            tree, validate, print_progress)

    ASSOCIATIVITY_OPERATORS = [ADD_OP, MULTIPLY_OP]

    def associativity(self, t):
        s = []
        if not t.op in self.ASSOCIATIVITY_OPERATORS:
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

    COMMUTATIVE_DISTRIBUTIVITY_OPERATOR_PAIRS = [(MULTIPLY_OP, ADD_OP)]
    # left-distributive: a * (b + c) == a * b + a * c
    LEFT_DISTRIBUTIVITY_OPERATOR_PAIRS = \
        COMMUTATIVE_DISTRIBUTIVITY_OPERATOR_PAIRS
    # Note that division '/' is only right-distributive over +
    RIGHT_DISTRIBUTIVITY_OPERATOR_PAIRS = \
        COMMUTATIVE_DISTRIBUTIVITY_OPERATOR_PAIRS

    LEFT_DISTRIBUTIVITY_OPERATORS, LEFT_DISTRIBUTION_OVER_OPERATORS = \
        zip(*LEFT_DISTRIBUTIVITY_OPERATOR_PAIRS)
    RIGHT_DISTRIBUTIVITY_OPERATORS, RIGHT_DISTRIBUTION_OVER_OPERATORS = \
        zip(*RIGHT_DISTRIBUTIVITY_OPERATOR_PAIRS)

    def distribute_for_distributivity(self, t):
        s = []
        if t.op in self.LEFT_DISTRIBUTIVITY_OPERATORS and is_expr(t.a2):
            if (t.op, t.a2.op) in self.LEFT_DISTRIBUTIVITY_OPERATOR_PAIRS:
                s.append(
                    Expr(op=t.a2.op,
                         a1=Expr(op=t.op, a1=t.a1, a2=t.a2.a1),
                         a2=Expr(op=t.op, a1=t.a1, a2=t.a2.a2)))
        if t.op in self.RIGHT_DISTRIBUTIVITY_OPERATORS and is_expr(t.a1):
            if (t.op, t.a1.op) in self.LEFT_DISTRIBUTIVITY_OPERATOR_PAIRS:
                s.append(
                    Expr(op=t.a1.op,
                         a1=Expr(op=t.op, a1=t.a1.a1, a2=t.a2),
                         a2=Expr(op=t.op, a1=t.a1.a2, a2=t.a2)))
        return s

    def collect_for_distributivity(self, t):
        op, a1, a2 = t
        if not op in (self.LEFT_DISTRIBUTION_OVER_OPERATORS +
                      self.RIGHT_DISTRIBUTION_OVER_OPERATORS):
            return
        # depth test
        if not is_expr(a1) and not is_expr(a2):
            return
        # expand by adding identities
        if is_expr(a2):
            op2, a21, a22 = a2
            if op2 == MULTIPLY_OP:
                if a21 == a1:
                    a1 = Expr(op=op2, a1=a1, a2=1L)
                elif a22 == a1:
                    a1 = Expr(op=op2, a1=1L, a2=a1)
        if is_expr(a1):
            op1, a11, a12 = a1
            if op1 == MULTIPLY_OP:
                if a11 == a2:
                    a2 = Expr(op=op1, a1=a2, a2=1L)
                elif a12 == a2:
                    a1 = Expr(op=op1, a1=1L, a2=a2)
        # must be all expressions
        if not is_expr(a1) or not is_expr(a2):
            return
        # equivalences
        op1, a11, a12 = a1
        op2, a21, a22 = a2
        if op1 != op2:
            return
        s = []
        if (op1, op) in self.LEFT_DISTRIBUTIVITY_OPERATOR_PAIRS:
            if a11 == a21:
                s.append(Expr(op=op1, a1=a11, a2=Expr(op=op, a1=a12, a2=a22)))
        if (op2, op) in self.RIGHT_DISTRIBUTIVITY_OPERATOR_PAIRS:
            if a12 == a22:
                s.append(Expr(op=op2, a1=Expr(op=op, a1=a11, a2=a21), a2=a12))
        return s

    def commutativity(self, t):
        return [Expr(op=t.op, a1=t.a2, a2=t.a1)]

    VAR_RE = re.compile(r"[^\d\W]\w*", re.UNICODE)

    def validate(self, t, tn):
        def vars(tree_str):
            return set(self.VAR_RE.findall(tree_str))
        to, no = ts, ns = str(t), str(tn)
        tsv, nsv = vars(ts), vars(ns)
        if tsv != nsv:
            raise ValidationError('Variable domain mismatch.')
        vv = {v: random.randint(0, 127) for v in tsv}
        for v, i in vv.iteritems():
            ts = re.sub(r'\b%s\b' % v, str(i), ts)
            ns = re.sub(r'\b%s\b' % v, str(i), ns)
        if eval(ts) != eval(ns):
            raise ValidationError(
                'Failed validation\n'
                'Original: %s %s,\n'
                'Transformed: %s %s' % (to, t, no, tn))

    def _identity_reduction(self, t, iop, i):
        if t.op != iop:
            return t
        if t.a1 == i:
            return t.a2
        if t.a2 == i:
            return t.a1
        return t

    def multiplicative_identity_reduction(self, t):
        return self._identity_reduction(t, MULTIPLY_OP, 1)

    def additive_identity_reduction(self, t):
        return self._identity_reduction(t, ADD_OP, 0)

    def zero_reduction(self, t):
        if t.op != MULTIPLY_OP:
            return t
        if t.a1 != 0 and t.a2 != 0:
            return t
        return 0

    def constant_reduction(self, t):
        if not is_num(t.a1) or not is_num(t.a2):
            return t
        if t.op == MULTIPLY_OP:
            return t.a1 * t.a2
        if t.op == ADD_OP:
            return t.a1 + t.a2
