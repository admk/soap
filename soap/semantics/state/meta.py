from soap import logger
from soap.common import indent
from soap.datatype import int_type
from soap.expression import (
    AccessExpr, Expression, SelectExpr, FixExpr, Variable,
    OutputVariableTuple, BinaryArithExpr, UpdateExpr, is_variable, operators
)
from soap.program.flow import AssignFlow, SkipFlow
from soap.semantics.error import cast, IntegerInterval
from soap.semantics.common import is_numeral
from soap.semantics.label import Label
from soap.semantics.state.base import BaseState
from soap.semantics.functions import expand_expr


class ForLoopExtractionFailureException(Exception):
    """Fails to extract for loop.  """


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
        raise TypeError(
            'Do not know how to convert {!r} into an expression'.format(value))

    def is_fixpoint(self, other):
        raise RuntimeError('Should not be called.')

    def widen(self, other):
        raise RuntimeError('Should not be called.')

    def visit_SkipFlow(self, flow):
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

    def _visit_loop(self, init_state, bool_expr, loop_flow):
        """
        Finds necessary loop variables and loop states for each variable.
        """
        bool_expr_vars = bool_expr.vars()
        input_vars = loop_flow.vars(output=False) | bool_expr_vars
        loop_vars = loop_flow.vars(input=False)
        id_state = self.__class__({k: k for k in input_vars | loop_vars})
        loop_state = id_state.transition(loop_flow)

        loop_map = {}
        init_map = {}

        for var in loop_vars:
            # local loop/init variables
            local_loop_vars = self._input_vars(loop_state, var)
            local_loop_vars |= bool_expr_vars
            # local loop/init states
            loop_map[var] = self.__class__(
                {k: v for k, v in loop_state.items() if k in local_loop_vars})
            init_map[var] = self.__class__(
                {k: v for k, v in init_state.items() if k in local_loop_vars})

        mapping = dict(init_state)
        for var in loop_map:
            # fixpoint expression
            mapping[var] = FixExpr(
                bool_expr, loop_map[var], var, init_map[var])
        return self.__class__(mapping)

    def visit_WhileFlow(self, flow):
        return self._visit_loop(self, flow.conditional_expr, flow.loop_flow)

    def visit_ForFlow(self, flow):
        init_state = self(flow.init_flow)
        return self._visit_loop(
            init_state, flow.conditional_expr, flow.loop_flow + flow.incr_flow)

    def format(self):
        items = []
        for k, v in sorted(self.items(), key=str):
            if isinstance(v, (Expression, MetaState)):
                v = v.format()
            items.append('{}: {}'.format(k, v))
        items = ', \n'.join(items)
        return '{{\n{}}}'.format(indent(items))

    def __str__(self):
        return self.format().replace('    ', '').replace('\n', '').strip()

    def __hash__(self):
        if self._hash is None:
            self._hash = hash(tuple(sorted(self.items(), key=hash)))
        return self._hash


def flow_to_meta_state(flow):
    id_state = MetaState({v: v for v in flow.vars(output=False)})
    return id_state.transition(flow)
