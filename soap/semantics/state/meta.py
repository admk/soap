from soap import logger
from soap.expression import (
    Expression, LinkExpr, FixExpr, expression_factory, is_expression,
    is_variable, operators, parse, Variable, FreeFlowVar
)
from soap.lattice.map import map
from soap.semantics.error import cast
from soap.semantics.common import is_numeral
from soap.semantics.state.base import BaseState


def _if_then_else(bool_expr, true_expr, false_expr):
    return expression_factory(
        operators.TERNARY_SELECT_OP, bool_expr, true_expr, false_expr)


class MetaState(BaseState, map(None, Expression)):
    __slots__ = ()

    def _cast_key(self, key):
        if isinstance(key, str):
            return Variable(key)
        if isinstance(key, Variable):
            return key
        raise TypeError(
            'Do not know how to convert {!r} into a variable'.format(key))

    def _cast_value(self, value=None, top=False, bottom=False):
        if top or bottom:
            return Expression(top=top, bottom=bottom)
        if isinstance(value, str):
            return parse(value)
        if isinstance(value, Expression):
            return value
        logger.warning(
            'TODO Not sure what to do with numerical values at the moment.')
        if isinstance(value, (int, float)):
            return cast(value)
        if is_numeral(value):
            return value
        raise TypeError(
            'Do not know how to convert {!r} into an expression'.format(value))

    def is_fixpoint(self, other):
        raise NotImplementedError('Should not be called.')

    def widen(self, other):
        raise NotImplementedError('Should not be called.')

    def visit_IdentityFlow(self, flow):
        return self

    def expand_expr(self, expr):
        if is_expression(expr):
            args = [self.expand_expr(a) for a in expr.args]
            return expression_factory(expr.op, *args)
        if is_variable(expr):
            return self[expr]
        if is_numeral(expr):
            return expr
        raise TypeError(
            'Do not know how to expand the expression {expr} with expression '
            'state {state}.'.format(expr=expr, state=self))

    def visit_AssignFlow(self, flow):
        return self[flow.var:self.expand_expr(flow.expr)]

    def visit_IfFlow(self, flow):
        bool_expr = self.expand_expr(flow.conditional_expr)
        true_state = self.transition(flow.true_flow)
        false_state = self.transition(flow.false_flow)
        var_list = set(self.keys())
        var_list |= set(true_state.keys()) | set(false_state.keys())
        state = self.empty()
        for var in var_list:
            if true_state[var] == false_state[var]:
                value = true_state[var]
            else:
                value = _if_then_else(
                    bool_expr, true_state[var], false_state[var])
            state[var] = value
        return state

    def visit_WhileFlow(self, flow):
        bool_expr = flow.conditional_expr
        loop_flow = flow.loop_flow
        var_list = loop_flow.vars()

        def fix_var(var):
            free_var = FreeFlowVar(name=var.name, flow=flow)
            id_state = self.__class__({k: k for k in var_list})
            loop_state = id_state.transition(loop_flow)
            true_expr = LinkExpr(free_var, loop_state)

            fix_expr = _if_then_else(bool_expr, true_expr, var)
            return FixExpr(free_var, fix_expr)

        mapping = dict(self)
        for k in var_list:
            mapping[k] = LinkExpr(fix_var(k), self)
        return self.__class__(mapping)
