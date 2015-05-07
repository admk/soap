from soap import logger
from soap.common import indent
from soap.datatype import int_type
from soap.expression import (
    AccessExpr, Expression, SelectExpr, FixExpr, ForExpr, Variable,
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

    def _construct_state_maps(self, bool_expr, loop_flow):
        """
        Finds necessary loop variables and loop states for each variable.
        """
        bool_expr_vars = bool_expr.vars()
        input_vars = loop_flow.vars(output=False) | bool_expr_vars
        loop_vars = loop_flow.vars(input=False)
        id_state = self.__class__({k: k for k in input_vars | loop_vars})
        loop_state = id_state.transition(loop_flow)

        loop_state_map = {}
        init_state_map = {}

        for var in loop_vars:
            # local loop/init variables
            local_loop_vars = self._input_vars(loop_state, var)
            local_loop_vars |= bool_expr_vars
            # local loop/init states
            loop_state_map[var] = self.__class__(
                {k: v for k, v in loop_state.items() if k in local_loop_vars})
            init_state_map[var] = self.__class__(
                {k: v for k, v in self.items() if k in local_loop_vars})

        return loop_state, loop_state_map, init_state_map

    def visit_WhileFlow(self, flow):
        bool_expr = flow.conditional_expr

        _, loop_state_map, init_state_map = self._construct_state_maps(
            bool_expr, flow.loop_flow)

        mapping = dict(self)
        for var in loop_state_map:
            # fixpoint expression
            mapping[var] = FixExpr(
                bool_expr, loop_state_map[var], var, init_state_map[var])

        return self.__class__(mapping)

    def _extract_for_loop_iter_space(self, flow, loop_state):
        is_constant = lambda val: (
            isinstance(val, IntegerInterval) and val.min == val.max)

        def to_constant(val):
            if not is_constant(val):
                raise ForLoopExtractionFailureException(
                    'Value is not constant.')
            return val.min

        bool_expr = flow.conditional_expr
        iter_var, stop = flow.conditional_expr.args
        if not is_variable(iter_var):
            raise ForLoopExtractionFailureException('Unrecognized iter_var.')
        if not iter_var.dtype == int_type:
            raise ForLoopExtractionFailureException('iter_var is not integer.')
        if stop != expand_expr(stop, loop_state):
            return False
        # stop = to_constant(stop)

        if bool_expr.op == operators.LESS_EQUAL_OP:
            if is_constant(stop):
                stop += 1
            else:
                stop = BinaryArithExpr(
                    operators.ADD_OP, stop, IntegerInterval(1))
        elif bool_expr.op not in [operators.LESS_OP, operators.EQUAL_OP]:
            raise ForLoopExtractionFailureException(
                'Unsupported compare operator.')

        init_flow = flow.init_flow
        if isinstance(init_flow, SkipFlow):
            # the initial value comes from ``self``
            start = self[iter_var]
        elif isinstance(init_flow, AssignFlow):
            if init_flow.var != iter_var:
                raise ForLoopExtractionFailureException('Mismatch iter_var.')
            start = init_flow.expr
        else:
            raise ForLoopExtractionFailureException('Unrecognized init_flow.')
        # start = to_constant(start)

        incr_flow = flow.incr_flow
        step_var, step_expr = incr_flow.var, incr_flow.expr
        arg_1, arg_2 = step_expr.args
        if step_var != iter_var:
            raise ForLoopExtractionFailureException('Mismatch iter_var.')
        if arg_1 == iter_var:
            step = arg_2
        elif arg_2 == iter_var:
            step = arg_1
        else:
            raise ForLoopExtractionFailureException('Mismatch iter_var.')
        if not is_constant(step):
            raise ForLoopExtractionFailureException('Step is not constant.')
        if step.min <= 0:
            raise ForLoopExtractionFailureException(
                'Step must be greater than 0.')

        return iter_var, start, stop, step

    def visit_ForFlow(self, flow):
        loop_flow = flow.loop_flow + flow.incr_flow
        loop_state, loop_state_map, init_state_map = \
            self._construct_state_maps(flow.conditional_expr, loop_flow)

        try:
            iter_var, start, stop, step = \
                self._extract_for_loop_iter_space(flow, loop_state)
        except ForLoopExtractionFailureException as e:
            logger.warning(str(e))
            return super().visit_ForFlow(flow)

        mapping = dict(self)
        for var in loop_state_map:
            # fixpoint expression
            var_loop_state = loop_state_map[var].immu_update(
                iter_var, iter_var)
            mapping[var] = ForExpr(
                iter_var, start, stop, step, var_loop_state, var,
                init_state_map[var])

        return self.__class__(mapping)

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
