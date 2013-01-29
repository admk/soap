#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


__author__ = 'Xitong Gao'
__email__ = 'xtg08@ic.ac.uk'


ADD_OP = '+'
MULTIPLY_OP = '*'

_OPERATORS = [ADD_OP, MULTIPLY_OP]


def _parse_r(s):
    s = s.strip()
    bracket_level = 0
    operator_pos = -1
    for i, v in enumerate(s):
        if v == '(':
            bracket_level += 1
        if v == ')':
            bracket_level -= 1
        if bracket_level == 1 and v in _OPERATORS:
            operator_pos = i
            break
    if operator_pos == -1:
        return s
    return (s[operator_pos],
            _parse_r(s[1:operator_pos].strip()),
            _parse_r(s[operator_pos + 1:-1].strip()))


def _unparse_r(t):
    if type(t) is str:
        return t
    operator, arg1, arg2 = t
    return '(' + _unparse_r(arg1) + operator + _unparse_r(arg2) + ')'


class ExprParser(object):

    def __init__(self, string_or_tree):
        super(ExprParser, self).__init__()
        if type(string_or_tree) is str:
            self.string = string_or_tree
        elif type(string_or_tree) is tuple:
            self.tree = string_or_tree

    @property
    def tree(self):
        return self._t

    @tree.setter
    def tree(self, t):
        self._t = t
        self._s = _unparse_r(t)

    @property
    def string(self):
        return self._s

    @string.setter
    def string(self, s):
        self._s = s
        self._t = _parse_r(self._s)

    def __str__(self):
        return self.string


class TreeTransformer(object):

    class TreeTransformerCore(object):

        def __init__(self, tree):
            super(TreeTransformer.TreeTransformerCore, self).__init__()
            self._t = tree

        def closure(self, f):
            trees = set([self._t])
            prev_trees = None
            while trees != prev_trees:
                prev_trees = trees
                trees_list = [set(self._walk_r(t, f)) for t in trees]
                trees = reduce(lambda x, y: x | y, trees_list)
            return trees

        def _walk_r(self, t, f):
            if type(t) is tuple:
                for e in set(f(t)):
                    yield e
                for e in set(self._walk_r(t[1], f)):
                    yield (t[0], e, t[2])
                for e in set(self._walk_r(t[2], f)):
                    yield (t[0], t[1], e)
            # make sure identity is not forgotten
            yield t

    def __init__(self, tree):
        super(TreeTransformer, self).__init__()
        self._t = tree

    def closure(self):
        """Perform transforms until transitive closure is reached.

        Returns:
            A set of trees after transform.
        """
        return TreeTransformer.TreeTransformerCore(self._t).closure(
                self._transform_collate)

    def _transform_collate(self, t):
        """Combines all transform methods into one.

        Args:
            t: A tree under transform.

        Returns:
            A set of trees after transform.
        """
        return reduce(
                lambda x, y: x | y,
                [set(f(t)) for f in self._transform_methods()])

    def _transform_methods(self):
        """Find all transform methods within the class

        Returns:
            A list of tuples containing method names and corresponding methods
            that can be called with a tree as the argument for each method.
        """
        methods = [member[0] for member in inspect.getmembers(
                self.__class__, predicate=inspect.ismethod)]
        return [getattr(self, method)
                for method in methods if method.endswith('tivity')]


class ExprTreeTransformer(TreeTransformer):

    def __init__(self, tree):
        super(ExprTreeTransformer, self).__init__(tree)

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

    def distributivity(self, t):
        return []

    def commutativity(self, t):
        return [(t[0], t[2], t[1])]


if __name__ == '__main__':
    e = '((a + b) + c)'
    t = ExprParser(e).tree
    print 'Expr:', e
    print 'Tree:', t
    s = ExprTreeTransformer(t).closure()
    print 'Transformed Total:', len(s)
    print 'Exprs:', s
