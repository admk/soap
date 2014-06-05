from soap.expression import (
    Expression, SelectExpr, StateGetterExpr, LinkExpr, FixExpr, Variable,
    parse
)
from soap.label.base import Label, LabelContext
from soap.lattice.map import map
from soap.semantics.error import cast
from soap.semantics.common import is_numeral
from soap.semantics.label import LabelSemantics
from soap.semantics.state.base import BaseState
from soap.semantics.state.functions import expand_expr, to_meta_state


def link_label_merge(env, context):
    # Transforms mapping: var -> target_expr * meta_state
    # into the form: meta_state -> var -> target_expr
    new_env = dict(env)
    meta_state_var_target = {}
    meta_state_link_meta_state = {}
    shared_meta_state = {}

    for var, expr in env.items():
        if not isinstance(expr, LinkExpr):
            continue

        # note that meta_state here is a label
        meta_state = expr.meta_state

        # update shared_meta_state by merging meta_state with it, and create
        # new meta_state by linking expressions from shared_meta_state
        link_meta_state = {}
        for meta_state_var, meta_state_expr in env[meta_state].items():
            if isinstance(meta_state_var, Variable):
                # var is a variable, don't add in shared_meta_state, but add in
                # link_meta_state
                link_meta_state[meta_state_var] = meta_state_expr
            elif isinstance(meta_state_var, Label):
                # var is a label, meaning it belongs to shared_meta_state
                shared_meta_state[meta_state_var] = meta_state_expr
            else:
                raise TypeError('Unrecognized type of key in meta_state.')
        meta_state_link_meta_state[meta_state] = link_meta_state

        # remove references to meta_state in new_env, since it will be taken
        # care of by shared_meta_state
        try:
            del new_env[meta_state]
        except KeyError:
            pass

        # get existing var -> target_expr labelling env, if not exist, get {}
        var_target = meta_state_var_target.setdefault(meta_state, {})

        # let variable maps to the target_expr label
        var_target[var] = expr.target_expr

        # update var_target with the labelling of target_expr
        var_target.update(env[expr.target_expr])

        # remove references to labelling of expr.target_expr in new_env
        del new_env[expr.target_expr]

    # add shared_meta_state to new_env
    shared_meta_state_label = context.Label(MetaState(shared_meta_state))
    if shared_meta_state:
        # only add shared_meta_state to env if it contains something
        new_env[shared_meta_state_label] = shared_meta_state

    # change env values where variable maps to a LinkExpr with shared
    # .meta_state, such that .target_expr could also share subexpressions
    for var, expr in env.items():
        # variable does not map to a LinkExpr
        if not isinstance(expr, LinkExpr):
            if isinstance(expr, Expression):
                # if expr is an expression, get its label
                label = context.Label(expr)
            elif isinstance(expr, Label):
                label = expr
            elif is_numeral(expr) or isinstance(expr, dict):
                continue
            else:
                raise TypeError('Unrecognized expression type.')
            if label in shared_meta_state:
                # found our label in shared_meta_state, reuse it
                new_env[var] = label
                # replace references in new_env about label, effectively remove
                # references in new_env about the expression being shared
                new_env[label] = StateGetterExpr(
                    shared_meta_state_label, label)
            continue

        meta_state = expr.meta_state

        # get shared env constructed previously
        var_target = meta_state_var_target[meta_state]

        # crazy, should recursively merge shared expressions, since merging
        # creates new opportunities for further subexpression state merging
        var_target = link_label_merge(var_target, context)

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

        # labelling for link_meta_state
        link_meta_state = meta_state_link_meta_state[meta_state]
        link_meta_state_label = context.Label(MetaState(link_meta_state))
        new_env[link_meta_state_label] = link_meta_state

        # labelling for link_meta_state * shared_meta_state
        new_meta_state = LinkExpr(
            link_meta_state_label, shared_meta_state_label)
        new_meta_state_label = context.Label(new_meta_state)
        new_env[new_meta_state_label] = new_meta_state

        # labelling for LinkExpr
        new_env[var] = LinkExpr(getter_label, new_meta_state_label)

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
        var_list = loop_flow.vars(output=False)

        def fix_var(var):
            id_state = self.__class__({k: k for k in var_list})
            loop_state = id_state.transition(loop_flow)
            return FixExpr(bool_expr, loop_state, var)

        meta_state = self.__class__(
            {k: v for k, v in self.items() if k in var_list})
        mapping = dict(self)
        for k in var_list:
            mapping[k] = LinkExpr(fix_var(k), meta_state)
        return self.__class__(mapping)

    def label(self, context=None):
        context = context or LabelContext(self)

        env = {}
        # FIXME nondeterminism in labelling
        for var, expr in sorted(self.items()):
            expr_label, expr_env = expr.label(context)
            env.update(expr_env)
            env[var] = expr_label
        env = link_label_merge(env, context)
        label = context.Label(MetaState(env))

        return LabelSemantics(label, env)


def flow_to_meta_state(flow):
    if isinstance(flow, str):
        from soap.program import parser
        flow = parser.parse(flow)
    return to_meta_state(flow)
