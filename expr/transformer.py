#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


from __future__ import print_function
import re
import sys
import random
import inspect

from common import ADD_OP, MULTIPLY_OP
from parser import ExprParser


__author__ = 'Xitong Gao'
__email__ = 'xtg08@ic.ac.uk'


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
    if type(t) is not tuple:
        return s
    for e in f(t):
        s.add(e)
    for e in _walk_r(t[1], f, v, c):
        s.add((t[0], e, t[2]))
    for e in _walk_r(t[2], f, v, c):
        s.add((t[0], t[1], e))
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
        print('Violating transformation:', f)
        raise
    return s


def item_to_list(f):
    def decorator(t):
        return [f(t)]
    return decorator


class ValidationError(Exception):
    """Failed to find equivalence."""


class TreeTransformer(object):

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
                    trees = _step(trees, f, v, True)
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
        return self._list_methods(lambda m: m.endswith('reduction'))

    def _transform_methods(self):
        return self._list_methods(lambda m: m.endswith('tivity'))

    def _list_methods(self, predicate):
        """Find all transform methods within the class that satisfies the
        predicate.

        Returns:
            A list of tuples containing method names and corresponding methods
            that can be called with a tree as the argument for each method.
        """
        methods = [member[0] for member in inspect.getmembers(
                self.__class__, predicate=inspect.ismethod)]
        return [getattr(self, method) for method in methods
                if not method.startswith('_') and predicate(method)]


class ExprTreeTransformer(TreeTransformer):

    def __init__(self, tree, validate=False, print_progress=False):
        super(ExprTreeTransformer, self).__init__(
                tree, validate, print_progress)

    ASSOCIATIVITY_OPERATORS = [ADD_OP, MULTIPLY_OP]

    def associativity(self, t):
        op, arg1, arg2 = t
        s = []
        if not op in self.ASSOCIATIVITY_OPERATORS:
            return []
        if type(arg1) is tuple:
            arg1_op, arg11, arg12 = arg1
            if arg1_op == op:
                s.append((op, arg11, (op, arg12, arg2)))
        if type(arg2) is tuple:
            arg2_op, arg21, arg22 = arg2
            if arg2_op == op:
                s.append((op, (op, arg1, arg21), arg22))
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
        op, arg1, arg2 = t
        s = []
        if op in self.LEFT_DISTRIBUTIVITY_OPERATORS and \
                type(arg2) is tuple:
            op2, arg21, arg22 = arg2
            if (op, op2) in self.LEFT_DISTRIBUTIVITY_OPERATOR_PAIRS:
                s.append((op2, (op, arg1, arg21), (op, arg1, arg22)))
        if op in self.RIGHT_DISTRIBUTIVITY_OPERATORS and \
                type(arg1) is tuple:
            op1, arg11, arg12 = arg1
            if (op, op1) in self.LEFT_DISTRIBUTIVITY_OPERATOR_PAIRS:
                s.append((op1, (op, arg11, arg2), (op, arg12, arg2)))
        return s

    def collect_for_distributivity(self, t):
        op, arg1, arg2 = t
        if not op in (self.LEFT_DISTRIBUTION_OVER_OPERATORS +
                    self.RIGHT_DISTRIBUTION_OVER_OPERATORS):
            return []
        # depth test
        if type(arg1) is not tuple and type(arg2) is not tuple:
            return []
        # tuplify by adding identities
        if type(arg2) is tuple:
            op2, arg21, arg22 = arg2
            if op2 == MULTIPLY_OP:
                if arg21 == arg1:
                    arg1 = (op2, arg1, 1)
                elif arg22 == arg1:
                    arg1 = (op2, 1, arg1)
        if type(arg1) is tuple:
            op1, arg11, arg12 = arg1
            if op1 == MULTIPLY_OP:
                if arg11 == arg2:
                    arg2 = (op1, arg2, 1)
                elif arg12 == arg2:
                    arg2 = (op1, 1, arg2)
        # must be all tuples
        if type(arg1) is not tuple or type(arg2) is not tuple:
            return []
        # equivalences
        op1, arg11, arg12 = arg1
        op2, arg21, arg22 = arg2
        if op1 != op2:
            return []
        s = []
        if (op1, op) in self.LEFT_DISTRIBUTIVITY_OPERATOR_PAIRS:
            if arg11 == arg21:
                s.append((op1, arg11, (op, arg12, arg22)))
        if (op1, op) in self.RIGHT_DISTRIBUTIVITY_OPERATOR_PAIRS and \
                (op2, op) in self.RIGHT_DISTRIBUTIVITY_OPERATOR_PAIRS:
            if arg12 == arg22:
                s.append((op2, (op, arg11, arg21), arg12))
        return s

    def commutativity(self, t):
        return [(t[0], t[2], t[1])]

    VAR_RE = re.compile(r"[^\d\W]\w*", re.UNICODE)

    def validate(self, t, tn):
        def string(tree):
            return ExprParser(tree).string
        def vars(tree_str):
            return set(self.VAR_RE.findall(tree_str))
        to, no = ts, ns = string(t), string(tn)
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
        op, arg1, arg2 = t
        if op != iop:
            return t
        if arg1 == i:
            return arg2
        if arg2 == i:
            return arg1
        return t

    def multiplicative_identity_reduction(self, t):
        return self._identity_reduction(t, MULTIPLY_OP, 1)

    def additive_identity_reduction(self, t):
        return self._identity_reduction(t, ADD_OP, 0)

    def zero_reduction(self, t):
        op, arg1, arg2 = t
        if op != MULTIPLY_OP:
            return t
        if arg1 != 0 and arg2 != 0:
            return t
        return 0
