from soap.expression import (
    Expression, SelectExpr, FixExpr, Variable, OutputVariableTuple, parse
)
from soap.label.base import Label, LabelContext
from soap.lattice.map import map
from soap.semantics.error import cast
from soap.semantics.common import is_numeral
from soap.semantics.label import LabelSemantics
from soap.semantics.state.base import BaseState
from soap.semantics.state.functions import expand_expr, to_meta_state


class MetaState(BaseState, map(None, Expression)):
    __slots__ = ()

    def _cast_key(self, key):
        if isinstance(key, str):
            return Variable(key)
        if isinstance(key, (Variable, Label, OutputVariableTuple)):
            return key
        raise TypeError(
            'Do not know how to convert {!r} into a variable'.format(key))

    def _cast_value(self, value=None, top=False, bottom=False):
        if top or bottom:
            return Expression(top=top, bottom=bottom)
        if isinstance(value, str):
            return parse(value)
        if isinstance(value, (Label, Expression)):
            return value
        if isinstance(value, (int, float)) or is_numeral(value):
            return cast(value)
        if isinstance(value, dict):
            return self.__class__(value)
        raise TypeError(
            'Do not know how to convert {!r} into an expression'.format(value))

    def is_fixpoint(self, other):
        raise RuntimeError('Should not be called.')

    def widen(self, other):
        raise RuntimeError('Should not be called.')

    def visit_IdentityFlow(self, flow):
        return self

    def visit_AssignFlow(self, flow):
        return self[flow.var:expand_expr(self, flow.expr)]

    def visit_IfFlow(self, flow):
        def get(state, var):
            expr = state[var]
            if expr.is_bottom():
                return var
            return expr
        bool_expr = expand_expr(self, flow.conditional_expr)
        true_state = self.transition(flow.true_flow)
        false_state = self.transition(flow.false_flow)
        var_list = set(self.keys())
        var_list |= set(true_state.keys()) | set(false_state.keys())
        mapping = dict(self)
        for var in var_list:
            true_expr = get(true_state, var)
            false_expr = get(false_state, var)
            if true_expr == false_expr:
                value = true_expr
            else:
                value = SelectExpr(bool_expr, true_expr, false_expr)
            mapping[var] = value
        return self.__class__(mapping)

    def visit_WhileFlow(self, flow):
        bool_expr = flow.conditional_expr
        loop_flow = flow.loop_flow

        bool_expr_vars = bool_expr.vars()
        # variables changed in loop
        loop_vars = loop_flow.vars(input=False)
        # input variables
        init_vars = flow.vars(output=False)
        # variables required by loop to iterate
        iter_vars = bool_expr_vars & loop_vars

        # loop_state for all output variables
        id_state = self.__class__({k: k for k in loop_vars})
        loop_state = id_state.transition(loop_flow)

        mapping = dict(self)
        for var in loop_vars:
            # local loop/init variables
            local_loop_vars = iter_vars | {var}
            local_init_vars = bool_expr_vars | local_loop_vars
            # local loop/init states
            local_loop_state = self.__class__(
                {k: v for k, v in loop_state.items() if k in local_loop_vars})
            local_init_state = self.__class__(
                {k: v for k, v in self.items() if k in local_init_vars})
            # fixpoint expression
            mapping[var] = FixExpr(
                bool_expr, local_loop_state, var, local_init_state)
        return self.__class__(mapping)

    def label(self, context=None):
        context = context or LabelContext(self)

        env = {}
        # FIXME better determinism in labelling, currently uses str-based
        # sorting, could use context.out_vars to traverse trees
        for var, expr in sorted(self.items(), key=str):
            expr_label, expr_env = expr.label(context)
            env.update(expr_env)
            env[var] = expr_label
        label = context.Label(MetaState(env))

        return LabelSemantics(label, env)


def flow_to_meta_state(flow):
    if isinstance(flow, str):
        from soap.program import parser
        flow = parser.parse(flow)
    return to_meta_state(flow)
