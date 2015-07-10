import itertools

import islpy

from soap.expression import (
    expression_factory, expression_variables, AccessExpr, UpdateExpr, Subscript
)
from soap.transformer.common import GenericExecuter


class ExpressionNotLinearException(Exception):
    pass


def _basic_set_from_linear_expressions(*expr_set):
    var_set = set()
    for expr in expr_set:
        var_set |= expression_variables(expr)

    problem = '{{ [{var_set}] : {equalities} }}'.format(
        var_set=', '.join(str(v) for v in var_set),
        equalities=' = '.join(str(e) for e in expr_set))
    try:
        basic_set = islpy.BasicSet(problem)
    except islpy.Error:
        raise ExpressionNotLinearException
    return basic_set


def linear_expressions_always_equal(*args):
    try:
        return _basic_set_from_linear_expressions(*args).is_universe()
    except ExpressionNotLinearException:
        return False


def linear_expressions_never_equal(*args):
    try:
        return _basic_set_from_linear_expressions(*args).is_empty()
    except ExpressionNotLinearException:
        return False


def subscripts_always_equal(*subscripts):
    return all(
        linear_expressions_always_equal(*indices)
        for indices in zip(*(a.args for a in subscripts)))


def subscripts_never_equal(*subscripts):
    return any(
        linear_expressions_never_equal(*indices)
        for indices in zip(*(a.args for a in subscripts)))


class AccessUpdateSimplifier(GenericExecuter):
    def _execute_atom(self, expr):
        return expr

    def _execute_args(self, expr):
        return (self(arg) for arg in expr.args)

    def _execute_expression(self, expr):
        return expression_factory(expr.op, *self._execute_args(expr))

    def execute_AccessExpr(self, expr):
        expr = self._execute_expression(expr)
        var, access_subscript = expr.args
        if not isinstance(var, UpdateExpr):
            return expr
        var, update_subscript, update_expr = self._execute_args(var)
        if subscripts_always_equal(update_subscript, access_subscript):
            # access(update(a, i, e), i) ==> e
            return update_expr
        if subscripts_never_equal(update_subscript, access_subscript):
            # access(update(a, i, _), j) ==> access(a, j)  [i != j]
            return self(AccessExpr(var, access_subscript))
        return expr

    def execute_UpdateExpr(self, expr):
        expr = self._execute_expression(expr)
        var, subscript, item_expr = expr.args
        if not isinstance(var, UpdateExpr):
            return expr
        var, last_subscript, _ = self._execute_args(var)
        if subscripts_always_equal(last_subscript, subscript):
            # update(update(a, i, _), i, e) ==> update(a, i, e)
            return self(UpdateExpr(var, subscript, item_expr))
        return expr

    def _execute_mapping(self, expr):
        return expr.__class__({
            var: self(var_expr) for var, var_expr in expr.items()})


class IndexCollector(GenericExecuter):
    def _execute_atom(self, expr, indices):
        pass

    def _execute_expression(self, expr, indices):
        for arg in expr.args:
            self(arg, indices)

    def execute_Subscript(self, expr, indices):
        for index in expr.args:
            indices.add(index)

    def _execute_mapping(self, expr, indices):
        for var_expr in expr.values():
            self(var_expr, indices)

    def __call__(self, expr, indices=None):
        indices = indices or set()
        super().__call__(expr, indices)
        return indices


class SubscriptSimplifier(GenericExecuter):
    def _execute_atom(self, expr, indices):
        return expr

    def _execute_expression(self, expr, indices):
        args = (self(arg, indices) for arg in expr.args)
        return expression_factory(expr.op, *args)

    def execute_Subscript(self, expr, indices):
        args = (indices.get(index, index) for index in expr.args)
        return expression_factory(expr.op, *args)

    def _execute_mapping(self, expr, indices):
        return expr.__class__({
            var: self(var_expr, indices) for var, var_expr in expr.items()})


def _smallest_indices(indices):
    equiv_map = {}
    iterer = itertools.product(indices, repeat=2)
    for index_1, index_2 in iterer:
        if not subscripts_always_equal(
                Subscript(index_1), Subscript(index_2)):
            continue
        equiv_set_1 = equiv_map.get(index_1)
        equiv_set_2 = equiv_map.get(index_2)
        if equiv_set_1 and equiv_set_2:
            if id(equiv_set_1) != id(equiv_set_2):
                raise ValueError('Equivalent set must be identical.')
        equiv_set = equiv_set_1 or equiv_set_2 or set()
        equiv_map.setdefault(index_1, equiv_set)
        equiv_map.setdefault(index_2, equiv_set)
        equiv_set |= {index_1, index_2}

    # simplify
    for index, equiv_set in equiv_map.items():
        equiv = sorted(equiv_set, key=lambda e: (len(str(e)), hash(e)))
        equiv_map[index] = equiv[0]

    return equiv_map


_access_update_simplify = AccessUpdateSimplifier()
_index_collect = IndexCollector()
_subscript_simplify = SubscriptSimplifier()


def linear_algebra_simplify(expr):
    expr = _access_update_simplify(expr)
    smallest_map = _smallest_indices(_index_collect(expr))
    return _subscript_simplify(expr, smallest_map)
