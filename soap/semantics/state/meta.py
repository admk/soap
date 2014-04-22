from soap.expression import (
    Expression, StateGetterExpr, LinkExpr, FixExpr, expression_factory,
    operators, parse, Variable, FreeFlowVar
)
from soap.label.base import Label, LabelContext
from soap.lattice.map import map
from soap.semantics.error import cast
from soap.semantics.common import is_numeral
from soap.semantics.label import LabelSemantics
from soap.semantics.state.base import BaseState
from soap.semantics.state.functions import expand_expr


def _if_then_else(bool_expr, true_expr, false_expr):
    return expression_factory(
        operators.TERNARY_SELECT_OP, bool_expr, true_expr, false_expr)


def _label_merge(env, context):
    # Transforms mapping: var -> target_expr * meta_state
    # into the form: meta_state -> var -> target_expr
    new_env = dict(env)
    meta_state_var_target = {}

    for var, expr in env.items():
        if not isinstance(expr, LinkExpr):
            continue

        # get existing var -> target_expr labelling env, if not exist, get {}
        var_target = meta_state_var_target.setdefault(expr.meta_state, {})

        # let variable maps to the target_expr label
        var_target[var] = expr.target_expr

        # update var_target with the labelling of target_expr
        var_target.update(env[expr.target_expr])

        # remove references to labelling of expr.target_expr in new_env
        del new_env[expr.target_expr]

    # change env values where variable maps to a LinkExpr with shared
    # .meta_state, such that .target_expr could also share subexpressions
    for var, expr in env.items():
        # variable does not map to a LinkExpr
        if not isinstance(expr, LinkExpr):
            continue

        meta_state = expr.meta_state

        # get shared env constructed previously
        var_target = meta_state_var_target.get(meta_state)

        # crazy, should recursively merge shared expressions, since merging
        # creates new opportunities for further subexpression state merging
        var_target = _label_merge(var_target, context)

        # variable maps to a LinkExpr, subexpression sharing updates
        # labelling for variable
        if isinstance(var, Label):
            var_label = var
        else:
            var_label, var_label_env = var.label(context)
            new_env.update(var_label_env)

        # labelling for var_target
        var_target_label = context.Label(MetaState(var_target))
        new_env[var_target_label] = var_target

        # labelling for state getter expression
        getter_expr = StateGetterExpr(var_target_label, var_label)
        getter_label = context.Label(getter_expr)
        new_env[getter_label] = getter_expr

        # labelling for LinkExpr
        new_env[var] = LinkExpr(getter_label, meta_state)

    return new_env


class MetaState(BaseState, map(None, Expression)):
    __slots__ = ()

    def _cast_key(self, key):
        if isinstance(key, str):
            return Variable(key)
        if isinstance(key, (Variable, Label)):
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
        raise NotImplementedError('Should not be called.')

    def widen(self, other):
        raise NotImplementedError('Should not be called.')

    def visit_IdentityFlow(self, flow):
        return self

    def visit_AssignFlow(self, flow):
        return self[flow.var:expand_expr(self, flow.expr)]

    def visit_IfFlow(self, flow):
        bool_expr = expand_expr(self, flow.conditional_expr)
        true_state = self.transition(flow.true_flow)
        false_state = self.transition(flow.false_flow)
        var_list = set(self.keys())
        var_list |= set(true_state.keys()) | set(false_state.keys())
        mapping = dict(self)
        for var in var_list:
            if true_state[var] == false_state[var]:
                value = true_state[var]
            else:
                value = _if_then_else(
                    bool_expr, true_state[var], false_state[var])
            mapping[var] = value
        return self.__class__(mapping)

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

    def label(self, context=None):
        context = context or LabelContext(self)

        env = {}
        for var, expr in self.items():
            expr_label, expr_env = expr.label(context)
            env.update(expr_env)
            env[var] = expr_label
        env = _label_merge(env, context)
        label = context.Label(MetaState(env))

        return LabelSemantics(label, env)
