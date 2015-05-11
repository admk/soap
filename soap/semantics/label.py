import math
from collections import namedtuple

from soap import flopoco
from soap.common import cached, Comparable, Flyweight
from soap.context import context
from soap.datatype import type_of
from soap.expression import (
    External, FixExpr, is_expression, operators, OutputVariableTuple
)
from soap.semantics.common import is_numeral
from soap.semantics.error import ErrorSemantics, IntegerInterval


_label_map = {}
_label_context_maps = {}
_label_size = 0


def fresh_int(hashable, _lmap=_label_map):
    """
    Generates a fresh int for the label of `statement`, within the known
    label mapping `lmap`.
    """
    label_value = _lmap.get(hashable)
    if label_value is not None:
        return label_value
    global _label_size
    _label_size += 1
    _lmap[hashable] = _label_size
    _lmap[_label_size] = hashable
    return _label_size


label_namedtuple_type = namedtuple(
    'Label', ['label_value', 'bound', 'invariant', 'context_id'])


class Label(label_namedtuple_type, Flyweight):
    """Constructs a label for expression or statement `statement`"""
    __slots__ = ()

    def __new__(cls, statement, bound, invariant,
                context_id=None, _label_value=None):
        label_value = _label_value or fresh_int(statement)
        return super().__new__(cls, label_value, bound, invariant, context_id)

    def immu_update(self, bound=None, invariant=None):
        label = self.label_value
        bound = bound or self.bound
        invariant = invariant or self.invariant
        context_id = self.context_id
        return self.__class__(label, bound, invariant, context_id)

    def __getnewargs__(self):
        return (
            None, self.bound, self.invariant, self.context_id,
            self.label_value)

    @property
    def dtype(self):
        return type_of(self.bound)

    def expr(self):
        lmap = _label_context_maps[self.context_id]
        return lmap[self.label_value]

    def signal_name(self):
        return 's_{}'.format(self.label_value)

    def port_name(self):
        return 'p_{}'.format(self.label_value)

    def __str__(self):
        s = 'l{}({})'.format(self.label_value, self.bound)
        return s

    def __repr__(self):
        formatter = '{cls}({label!r}, {bound!r}, {invariant!r}, {context!r})'
        return formatter.format(
            cls=self.__class__.__name__, label=self.label_value,
            bound=self.bound, invariant=self.invariant,
            context=self.context_id)


class LabelContext(object):
    def __init__(self, description, out_vars=None):
        super().__init__()
        if not isinstance(description, str):
            description = 'c{}'.format(
                Label(description, None, None).label_value)
        self.description = description
        self.out_vars = out_vars
        self.lmap = _label_context_maps.setdefault(self.description, {})

    def Label(self, statement, bound, invariant):
        label_value = fresh_int(statement, _lmap=self.lmap)
        return Label(
            statement, bound=bound, invariant=invariant,
            context_id=self.description, _label_value=label_value)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.description == other.description

    def __repr__(self):
        return '<{cls}:{description}>'.format(
            cls=self.__class__, description=self.description)


_FILTER_OPERATORS = operators.TRADITIONAL_OPERATORS + [
    operators.TERNARY_SELECT_OP
]


@cached
def _datatype_exponent(op, label):
    if isinstance(label, OutputVariableTuple):
        exponent = 0
        for l in label:
            label_datatype, label_exponent = _datatype_exponent(op, l)
            exponent += label_exponent
        return None, exponent

    if op == operators.FIXPOINT_OP:
        return None, 0
    if op not in _FILTER_OPERATORS:
        return None, None

    bound = label.bound
    datatype = type(bound)

    if datatype is IntegerInterval:
        if bound.is_top():
            return datatype, flopoco.wi_max
        if bound.is_bottom():
            return datatype, flopoco.wi_min
        bound_max = max(abs(bound.min), abs(bound.max), 1)
        width_max = int(math.ceil(math.log(bound_max + 1, 2)) + 1)
        return datatype, width_max

    if datatype is ErrorSemantics:
        bound = bound.v
        if bound.is_top():
            return datatype, flopoco.we_max
        if bound.is_bottom():
            return datatype, flopoco.we_min
        bound_max = max(abs(bound.min), abs(bound.max), 1)
        try:
            exp_max = math.floor(math.log(bound_max, 2))
        except OverflowError:
            return datatype, flopoco.we_max
        try:
            exponent = int(math.ceil(math.log(exp_max + 1, 2) + 1))
            return datatype, max(exponent, flopoco.we_min)
        except ValueError:
            return datatype, flopoco.we_min

    raise TypeError('Unrecognized type of bound {!r}'.format(bound))


_label_semantics_tuple_type = namedtuple('LabelSemantics', ['label', 'env'])


class s(namedtuple('Statistics', ['dsp', 'ff', 'lut'])):
    def __add__(self, other):
        dsp, ff, lut = [a + b for a, b in zip(self, other)]
        return self.__class__(dsp, ff, lut)


"""LegUp
_integer_table = {
    # dsp, ff, lut
    'comparison': s(0, 65, 35),
    operators.ADD_OP: s(0, 96, 32),
    operators.SUBTRACT_OP: s(0, 96, 32),
    operators.MULTIPLY_OP: s(4, 96, 0),
    operators.DIVIDE_OP: s(0, 96, 1247),
    operators.UNARY_SUBTRACT_OP: s(0, 96, 32),
    operators.TERNARY_SELECT_OP: s(0, 96, 32),
    operators.FIXPOINT_OP: s(0, 96, 32),
    operators.BARRIER_OP: s(0, 0, 0),
    operators.SUBTRACT_OP: s(0, 0, 0),
    operators.INDEX_ACCESS_OP: s(0, 0, 0),
    operators.INDEX_UPDATE_OP: s(0, 0, 0),
}
_single_table = {
    'conversion': s(0, 211, 186),
    'comparison': s(0, 33, 68),
    operators.ADD_OP: s(0, 540, 505),
    operators.SUBTRACT_OP: s(0, 540, 505),
    operators.MULTIPLY_OP: s(4, 222, 141),
    operators.DIVIDE_OP: s(0, 2788, 3198),
    operators.UNARY_SUBTRACT_OP: s(0, 0, 1),
    operators.TERNARY_SELECT_OP: s(0, 96, 32),
    operators.FIXPOINT_OP: s(0, 96, 32),
    operators.BARRIER_OP: s(0, 0, 0),
    operators.SUBTRACT_OP: s(0, 0, 0),
    operators.INDEX_ACCESS_OP: s(0, 0, 0),
    operators.INDEX_UPDATE_OP: s(0, 0, 0),
}
_double_table = {}
"""
# Xilinx Vivado
_integer_table = {
    'comparison': s(0, 0, 39),
    operators.ADD_OP: s(0, 0, 32),
    operators.SUBTRACT_OP: s(0, 0, 32),
    operators.MULTIPLY_OP: s(4, 45, 21),
    operators.DIVIDE_OP: s(0, 1712, 1779),
    operators.UNARY_SUBTRACT_OP: s(0, 0, 32),
    operators.TERNARY_SELECT_OP: s(0, 0, 71),
    operators.FIXPOINT_OP: s(0, 0, 71),
    operators.BARRIER_OP: s(0, 0, 0),
}
_single_table = {
    'conversion': s(0, 128, 519),
    'comparison': s(0, 66, 239),
    operators.ADD_OP: s(2, 227, 400),
    operators.SUBTRACT_OP: s(2, 227, 400),
    operators.MULTIPLY_OP: s(3, 128, 324),
    operators.DIVIDE_OP: s(0, 363, 986),
    operators.UNARY_SUBTRACT_OP: s(0, 0, 37),
    operators.TERNARY_SELECT_OP: s(0, 0, 71),
    operators.FIXPOINT_OP: s(0, 0, 0),
    operators.BARRIER_OP: s(0, 0, 0),
}
_double_table = {
    'conversion': s(0, 189, 578),
    'comparison': s(0, 130, 578),
    operators.ADD_OP: s(3, 445, 1144),
    operators.SUBTRACT_OP: s(3, 445, 1144),
    operators.MULTIPLY_OP: s(11, 299, 570),
    operators.DIVIDE_OP: s(0, 1710, 3623),
    operators.UNARY_SUBTRACT_OP: s(0, 0, 81),
    operators.TERNARY_SELECT_OP: s(0, 0, 103),
    operators.FIXPOINT_OP: s(0, 0, 0),
    operators.BARRIER_OP: s(0, 0, 0),
}


class LabelSemantics(_label_semantics_tuple_type, Flyweight, Comparable):
    """The semantics that captures the area of an expression."""
    def __new__(cls, label, env):
        from soap.semantics.state import MetaState
        if not isinstance(env, MetaState):
            env = MetaState(env)
        return super().__new__(cls, label, env)

    @cached
    def resources(self, precision=None):
        """FIXME Emergency luts statistics for now"""
        precision = precision or context.precision
        if precision == 23:
            table = _single_table
        elif precision == 52:
            table = _double_table
        else:
            raise ValueError('Precision must be single (23) or double (52).')

        def accumulate_luts_count(env):
            stat = s(0, 0, 0)
            conversion_set = set()
            for label, expr in env.items():
                if is_expression(expr) and not isinstance(expr, External):
                    op = expr.op
                    if op in operators.COMPARISON_OPERATORS:
                        op = 'comparison'
                    if isinstance(label, Label):
                        datatype = type(label.bound)
                    else:
                        datatype = None
                    if datatype is IntegerInterval:
                        stat += _integer_table[op]
                    elif datatype is ErrorSemantics:
                        for arg in expr.args:
                            if not isinstance(arg, Label):
                                continue
                            if not isinstance(arg.bound, IntegerInterval):
                                continue
                            if is_numeral(env[arg]):
                                continue
                            conversion_set.add(arg)
                        stat += table[op]
                if isinstance(expr, FixExpr):
                    stat += accumulate_luts_count(expr.bool_expr[1])
                    stat += accumulate_luts_count(expr.loop_state)
                    stat += accumulate_luts_count(expr.init_state)
            dsp, ff, lut = table['conversion']
            no_conv = len(conversion_set)
            stat += s(no_conv * dsp, no_conv * ff, no_conv * lut)
            return stat

        return accumulate_luts_count(self.env)

    @cached
    def _alt_luts(self, precision=None):
        precision = precision or context.precision

        def accumulate_luts_count(env):
            luts = 0
            for label, expr in env.items():
                if is_expression(expr) and not isinstance(expr, External):
                    datatype, exponent = _datatype_exponent(expr.op, label)
                    luts += flopoco.operator_luts(
                        expr.op, datatype, exponent, precision)
                if isinstance(expr, FixExpr):
                    luts += accumulate_luts_count(expr.bool_expr[1])
                    luts += accumulate_luts_count(expr.loop_state)
                    luts += accumulate_luts_count(expr.init_state)
            return luts

        return accumulate_luts_count(self.env)

    def expr(self):
        return self.label.expr()

    def __iter__(self):
        return iter((self.label, self.env))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.label == other.label and self.env == other.env

    def __hash__(self):
        return hash((self.label, self.env))

    def __str__(self):
        return '({}, {})'.format(self.label, self.env)
