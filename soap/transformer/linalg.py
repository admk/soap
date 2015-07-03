import islpy

from soap.expression import (
    expression_factory, expression_variables, AccessExpr, UpdateExpr
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


class LinearAlgebraSimplifier(GenericExecuter):
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
        if linear_expressions_always_equal(update_subscript, access_subscript):
            # access(update(a, i, e), i) ==> e
            return update_expr
        if linear_expressions_never_equal(update_subscript, access_subscript):
            # access(update(a, i, _), j) ==> access(a, j)  [i != j]
            return self(AccessExpr(var, access_subscript))
        return expr

    def execute_UpdateExpr(self, expr):
        expr = self._execute_expression(expr)
        var, subscript, item_expr = expr.args
        if not isinstance(var, UpdateExpr):
            return expr
        var, last_subscript, _ = self._execute_args(var)
        if linear_expressions_always_equal(last_subscript, subscript):
            # update(update(a, i, _), i, e) ==> update(a, i, e)
            return self(UpdateExpr(var, subscript, item_expr))
        return expr

    def _execute_mapping(self, expr):
        return expr.__class__({
            var: self(var_expr) for var, var_expr in expr.items()})


linear_algebra_simplify = LinearAlgebraSimplifier()
