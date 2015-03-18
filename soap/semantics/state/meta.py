from soap.expression import (
    AccessExpr, Expression, SelectExpr, FixExpr, Variable, OutputVariableTuple,
    UpdateExpr
)
from soap.semantics.error import cast
from soap.semantics.common import is_numeral
from soap.semantics.label import Label
from soap.semantics.state.base import BaseState
from soap.semantics.functions import expand_expr


class MetaState(BaseState, dict):
    __slots__ = ('_hash')

    def __init__(self, dictionary=None, **kwargs):
        dictionary = dict(dictionary or {}, **kwargs)
        mapping = {
            self._cast_key(key): self._cast_value(key, value)
            for key, value in dictionary.items()
        }
        super().__init__(mapping)
        self._hash = None

    def _cast_key(self, key):
        if isinstance(key, str):
            if key.startswith('__'):
                # internal data
                return key
            var_list = [var for var in self.keys() if var.name == key]
            if not var_list:
                raise KeyError(key)
            if len(var_list) > 1:
                raise KeyError('Multiple variables with the same name.')
            var = var_list.pop()
            return var
        if isinstance(key, (Variable, Label, OutputVariableTuple)):
            return key
        raise TypeError(
            'Do not know how to convert {!r} into a variable'.format(key))

    def _cast_value(self, key, value):
        if isinstance(value, (Label, Expression)):
            return value
        if isinstance(value, str):
            from soap.parser import parse
            return parse(value)
        if isinstance(value, (int, float)) or is_numeral(value):
            return cast(value)
        if isinstance(value, dict):
            return self.__class__(value)
        if key.startswith('__'):
            # internal data
            return value
        raise TypeError(
            'Do not know how to convert {!r} into an expression'.format(value))

    def immu_update(self, key, value):
        """
        Generate a new copy of this MetaState, and update the content with a
        new pair `key`: `value`.
        """
        new_mapping = dict(self)
        new_mapping[self._cast_key(key)] = self._cast_value(key, value)
        return self.__class__(new_mapping)

    def is_fixpoint(self, other):
        raise RuntimeError('Should not be called.')

    def widen(self, other):
        raise RuntimeError('Should not be called.')

    def visit_IdentityFlow(self, flow):
        return self

    def visit_AssignFlow(self, flow):
        var, expr = flow.var, flow.expr
        if isinstance(var, AccessExpr):
            var, subscript = var.var, var.subscript
            expr = UpdateExpr(var, subscript, expr)
        return self.immu_update(var, expand_expr(expr, self))

    def visit_IfFlow(self, flow):
        def get(state, var):
            expr = state[var]
            return expr
        bool_expr = expand_expr(flow.conditional_expr, self)
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

    @staticmethod
    def _input_vars(meta_state, var):
        in_vars = {var}
        next_vars = {var}
        while next_vars:
            var = next_vars.pop()
            expr = meta_state.get(var)
            if expr is None or is_numeral(expr):
                continue
            expr_vars = expr.vars()
            next_vars |= expr_vars - in_vars
            in_vars |= expr_vars
        return in_vars

    def visit_WhileFlow(self, flow):
        bool_expr = flow.conditional_expr
        loop_flow = flow.loop_flow
        bool_expr_vars = bool_expr.vars()

        # loop_state for all output variables
        input_vars = loop_flow.vars(output=False) | bool_expr_vars
        loop_vars = loop_flow.vars(input=False)
        id_state = self.__class__({k: k for k in input_vars | loop_vars})
        loop_state = id_state.transition(loop_flow)

        mapping = dict(self)
        for var in loop_vars:
            # local loop/init variables
            local_loop_vars = self._input_vars(loop_state, var)
            local_loop_vars |= bool_expr_vars
            # local loop/init states
            local_loop_state = self.__class__(
                {k: v for k, v in loop_state.items() if k in local_loop_vars})
            local_init_state = self.__class__(
                {k: v for k, v in self.items() if k in local_loop_vars})
            # fixpoint expression
            mapping[var] = FixExpr(
                bool_expr, local_loop_state, var, local_init_state)

        return self.__class__(mapping)

    def __hash__(self):
        if self._hash is None:
            self._hash = hash(tuple(sorted(self.items(), key=hash)))
        return self._hash


def flow_to_meta_state(flow):
    id_state = MetaState({v: v for v in flow.vars(output=False)})
    return id_state.transition(flow)
