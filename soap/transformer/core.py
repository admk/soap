"""
.. module:: soap.transformer.core
    :synopsis: Base class for transforming expression instances.
"""
import functools
import itertools
import multiprocessing
import sys

from soap import logger
from soap.common import cached
from soap.common.parallel import pool
from soap.expression.common import expression_factory, is_expression
from soap.parser import parse
from soap.transformer.pattern import transform
from soap.transformer.depth import crop, stitch


RECURSION_LIMIT = sys.getrecursionlimit()


class TreeFarmer(object):
    def __init__(self, depth):
        super().__init__()
        self.depth = depth

    def _harvest(self, trees):
        """Crops all trees at the depth limit."""
        if self.depth >= RECURSION_LIMIT:
            return trees
        logger.debug('Harvesting trees.')
        cropped = []
        for t in trees:
            try:
                t, e = crop(t, self.depth, self)
            except AttributeError:
                t, e = t, {}
            cropped.append(t)
            self._crop_env.update(e)
        return cropped

    def _seed(self, trees):
        """Stitches all trees."""
        logger.debug('Seeding trees.')
        if not self._crop_env:
            return trees
        seeded = set()
        for t in trees:
            try:
                t = stitch(t, self._crop_env)
            except AttributeError:
                pass
            seeded.add(t)
        return seeded


class TreeTransformer(TreeFarmer):
    """The base class that finds the transitive closure of transformed trees.

    :param tree_or_trees: An input expression, or a container of equivalent
        expressions.
    :type tree_or_trees: :class:`soap.expression.Expression`
    :param depth: The depth limit for equivalence finding, if not specified, a
        depth limit will not be used.
    :type depth: int or None
    :param step_plugin: A plugin function which is called after one step of
        transitive closure, it should take as argument a set of trees and
        return a new set of trees.
    :type step_plugin: function
    :param reduce_plugin: A plugin function which is called after one step of
        reduction, it should take as argument a set of trees and turn a new set
        of trees.
    :type reduce_plugin: function
    :param multiprocessing: If set, the class will multiprocess when computing
        new equivalent trees.
    :type multiprocessing: bool
    """
    transform_rules = {}
    reduction_rules = {}

    def __init__(self, tree_or_trees,
                 depth=None, transform_rules=None, reduction_rules=None,
                 step_plugin=None, reduce_plugin=None,
                 multiprocessing=True):
        super().__init__(depth=depth or RECURSION_LIMIT)
        self.multiprocessing = multiprocessing
        self.step_plugin = step_plugin
        self.reduce_plugin = reduce_plugin
        if transform_rules:
            self.transform_rules = transform_rules
        if reduction_rules:
            self.reduction_rules = reduction_rules
        if isinstance(tree_or_trees, str):
            self._expressions = [parse(tree_or_trees)]
        elif is_expression(tree_or_trees):
            self._expressions = [tree_or_trees]
        else:
            self._expressions = tree_or_trees
        self._crop_env = {}
        if self.depth >= RECURSION_LIMIT and self.transform_rules:
            logger.warning('Depth limit not set.', depth)

    def _plugin(self, trees, plugin):
        """Plugin function call setup and cleanup."""
        if not plugin:
            return trees
        trees = self._seed(trees)
        trees = plugin(trees)
        trees = set(self._harvest(trees))
        return trees

    def _step(self, expressions, closure=False, depth=None):
        """One step of the transitive closure."""
        rules = self.transform_rules if closure else self.reduction_rules
        if self.multiprocessing:
            cpu_count = multiprocessing.cpu_count()
            chunksize = int(len(expressions) / cpu_count) + 1
            # this gives the desired deterministic behaviour for reduction
            # so never change it to imap_unordered!!
            map = pool.map
        else:
            cpu_count = chunksize = 1
            map = lambda func, args_list, _: [func(args) for args in args_list]
        union = lambda s, _: functools.reduce(lambda x, y: x | y, s)
        args_list = [(expression, rules, closure, depth)
                     for index, expression in enumerate(expressions)]
        should_include, discovered_sets = \
            zip(*map(_walk, args_list, chunksize))
        expressions = {
            expression for index, expression in enumerate(expressions)
            if should_include[index]}
        discovered = union(discovered_sets, cpu_count)
        return expressions, discovered

    def _recursive_closure(self, trees, reduced=False):
        """Transitive closure algorithm."""
        done_trees = set()
        todo_trees = set(trees)
        i = 1
        while todo_trees:
            # print set size
            logger.persistent(
                'Iteration' if not reduced else 'Reduction', i)
            logger.persistent('Trees', len(done_trees))
            logger.persistent('Todo', len(todo_trees))
            if not reduced:
                _, step_trees = \
                    self._step(todo_trees, not reduced, None)
                step_trees -= done_trees
                step_trees = self._recursive_closure(step_trees, True)
                step_trees = self._plugin(step_trees, self.step_plugin)
                done_trees |= todo_trees
                todo_trees = step_trees - done_trees
            else:
                nore_trees, step_trees = \
                    self._step(todo_trees, not reduced, None)
                step_trees = self._plugin(step_trees, self.reduce_plugin)
                done_trees |= nore_trees
                todo_trees = step_trees - nore_trees
            i += 1
        logger.unpersistent('Iteration', 'Reduction', 'Trees', 'Todo')
        return done_trees

    def closure(self):
        """Perform transforms until transitive closure is reached.

        :returns: A set of trees after transform.
        """
        expressions = self._harvest(self._expressions)
        expressions = self._recursive_closure(expressions)
        expressions = self._seed(expressions)
        return expressions


def _walk(args):
    expression, rules, closure, depth = args
    discovered = set()
    depth = depth if closure and depth else RECURSION_LIMIT
    try:
        discovered = _recursive_walk(expression, rules, depth)
    except Exception:
        try:
            from IPython.core.ultratb import VerboseTB
        except ImportError:
            import traceback
            traceback.print_exc()
        else:
            import sys
            exc = sys.exc_info()
            print(VerboseTB().text(*exc))
        raise
    if closure:
        discovered.add(expression)
    return not closure and not discovered, discovered


@cached
def _recursive_walk(expression, rules, depth):
    """Tree walker"""
    discovered = set()
    if depth == 0:
        return discovered
    if not is_expression(expression):
        return discovered
    for rule in rules.get(expression.op, []):
        discovered |= transform(rule, expression)
    args_discovered = (_recursive_walk(a, rules, depth) | {a}
                       for a in expression.args)
    for args in itertools.product(*args_discovered):
        discovered.add(expression_factory(expression.op, *args))
    if expression in discovered:
        discovered.remove(expression)
    return discovered


def par_union(sl):
    return functools.reduce(lambda s, t: s | t, sl)


def _iunion(sl, no_processes):
    """Parallel set union, slower than serial implementation."""
    def chunks(l, n):
        for i in range(0, len(l), n):
            yield l[i:i+n]
    chunksize = int(len(sl) / no_processes) + 2
    while len(sl) > 1:
        sys.stdout.write('\rUnion: %d.' % len(sl))
        sys.stdout.flush()
        sl = pool.map_unordered(par_union, chunks(sl, chunksize))
    return sl.pop()
