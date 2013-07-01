import sys
import functools
import multiprocessing

import ce.logger as logger
from ce.logger import levels
from ce.common import cached
from ce.expr.common import is_expr
from ce.expr import Expr


RECURSION_LIMIT = sys.getrecursionlimit()


def item_to_list(f):
    def wrapper(t):
        v = f(t)
        return [v] if not v is None else []
    return functools.wraps(f)(wrapper)


def none_to_list(f):
    def wrapper(t):
        v = f(t)
        return v if not v is None else []
    return functools.wraps(f)(wrapper)


class ValidationError(Exception):
    """Failed to find equivalence."""


class TreeTransformer(object):

    transform_methods = None
    reduction_methods = None

    def __init__(self, tree_or_trees,
                 validate=False, depth=None,
                 step_plugin=None, reduce_plugin=None,
                 multiprocessing=True):
        try:
            self._t = [Expr(tree_or_trees)]
        except TypeError:
            self._t = tree_or_trees
        self._v = validate
        self._m = multiprocessing
        self._d = depth or RECURSION_LIMIT
        self._n = {}
        self._sp = step_plugin
        self._rp = reduce_plugin
        self.transform_methods = list(self.__class__.transform_methods or [])
        self.reduction_methods = list(self.__class__.reduction_methods or [])
        super().__init__()

    def _harvest(self, trees):
        if self._d >= RECURSION_LIMIT:
            return trees
        cropped = []
        for t in trees:
            try:
                t, e = t.crop(self._d)
            except AttributeError:
                t, e = t, {}
            cropped.append(t)
            self._n.update(e)
        return cropped

    def _seed(self, trees):
        if not self._n:
            return trees
        seeded = set()
        for t in trees:
            try:
                t = t.stitch(self._n)
            except AttributeError:
                pass
            seeded.add(t)
        return seeded

    def _plugin(self, trees, plugin):
        if not plugin:
            return trees
        trees = self._seed(trees)
        trees = plugin(trees)
        trees = set(self._harvest(trees))
        return trees

    def _closure_r(self, trees, reduced=False):
        v = self._validate if self._v else None
        done_trees = set()
        todo_trees = set(trees)
        i = 0
        while todo_trees:
            # print set size
            i += 1
            logger.persistent(
                'Iteration' if not reduced else 'Reduction', i,
                l=levels.debug)
            logger.persistent('Trees', len(done_trees), l=levels.debug)
            logger.persistent('Todo', len(todo_trees), l=levels.debug)
            if not reduced:
                f = self.transform_methods
                _, step_trees = \
                    _step(todo_trees, f, v, not reduced, self._d, self._m)
                step_trees -= done_trees
                step_trees = self._closure_r(step_trees, True)
                step_trees = self._plugin(step_trees, self._sp)
                done_trees |= todo_trees
                todo_trees = step_trees - done_trees
            else:
                f = self.reduction_methods
                nore_trees, step_trees = \
                    _step(todo_trees, f, v, not reduced, None, self._m)
                step_trees = self._plugin(step_trees, self._rp)
                done_trees |= nore_trees
                todo_trees = step_trees - nore_trees
        logger.unpersistent('Iteration', 'Reduction', 'Trees', 'Todo')
        return done_trees

    def closure(self):
        """Perform transforms until transitive closure is reached.

        Returns:
            A set of trees after transform.
        """
        s = self._harvest(self._t)
        s = self._closure_r(s)
        s = self._seed(s)
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


def _walk(t_fs_v_c_d):
    t, fs, v, c, d = t_fs_v_c_d
    s = set()
    for f in fs:
        s |= _walk_r(t, f, v, d if c else RECURSION_LIMIT)
    if c:
        s.add(t)
    return True if not c and not s else False, s


@cached
def _walk_r(t, f, v, d):
    s = set()
    if not is_expr(t):
        return s
    for e in f(t):
        s.add(e)
    for a, b in (t.args, t.args[::-1]):
        for e in _walk_r(a, f, v, d):
            s.add(Expr(t.op, e, b))
    if not v:
        return s
    try:
        for tn in s:
            v(t, tn)
    except ValidationError:
        logger.error('Violating transformation:', f.__name__)
        raise
    return s


def par_union(sl):
    return functools.reduce(lambda s, t: s | t, sl)


_pool = None


def pool():
    global _pool
    if _pool is None:
        _pool = multiprocessing.Pool()
    return _pool


def _iunion(sl, no_processes):
    def chunks(l, n):
        for i in range(0, len(l), n):
            yield l[i:i+n]
    chunksize = int(len(sl) / no_processes) + 2
    while len(sl) > 1:
        sys.stdout.write('\rUnion: %d.' % len(sl))
        sys.stdout.flush()
        sl = list(pool().imap_unordered(par_union, chunks(sl, chunksize)))
    return sl.pop()


def _step(s, fs, v=None, c=False, d=None, m=True):
    """Find the set of trees related by the function f.

    Args:
        s: A set of trees.
        fs: A set of functions which transforms the trees. Each function has
            one argument, the tree, and returns a set of trees after transform.
        v: A function which validates the transform.
        c: If set, it will include everything in s. Otherwise only derived
            trees.
        d: Depth of node traversal in trees.
        m: Whether multiprocessing is used.

    Returns:
        A set of trees related by f.
    """
    if m:
        cpu_count = multiprocessing.cpu_count()
        chunksize = int(len(s) / cpu_count) + 1
        map = pool().imap
    else:
        cpu_count = chunksize = 1
        map = lambda f, l, _: [f(a) for a in l]
    union = lambda s, _: functools.reduce(lambda x, y: x | y, s)
    r = [(t, fs, v, c, d) for i, t in enumerate(s)]
    b, r = list(zip(*map(_walk, r, chunksize)))
    s = {t for i, t in enumerate(s) if b[i]}
    r = union(r, cpu_count)
    return s, r
