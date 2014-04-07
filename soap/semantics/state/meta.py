from soap.expression import (
    Expression, expression_factory, is_expression, is_variable,
    operators, parse, Variable
)
from soap.lattice.map import map
from soap.semantics.error import cast
from soap.semantics.common import is_numeral
from soap.semantics.state.base import BaseState


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
        if is_numeral(value):
            raise NotImplementedError('TODO Not sure about this yet.')
            return cast(value)
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
        state = self.copy()
        state[flow.var] = self.expand_expr(flow.expr)
        return state

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
                value = expression_factory(
                    operators.TERNARY_SELECT_OP,
                    bool_expr, true_state[var], false_state[var])
            state[var] = value
        return state
