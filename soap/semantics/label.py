import math
from collections import namedtuple

from soap import flopoco
from soap.common import cached, Comparable, Flyweight, superscript
from soap.context import context
from soap.expression import (
    External, FixExpr, is_expression, operators, OutputVariableTuple
)
from soap.lattice.base import Lattice
from soap.semantics.common import is_numeral
from soap.semantics.error import ErrorSemantics, IntegerInterval


_label_map = {}
_label_context_maps = {}


class _Dummy(object):
    def __hash__(self):
        return id(self)


def fresh_int(hashable, lmap=_label_map):
    """
    Generates a fresh int for the label of `statement`, within the known
    label mapping `lmap`.
    """
    if hashable is None:
        hashable = _Dummy()
    return lmap.setdefault(hashable, len(lmap) + 1)


label_namedtuple_type = namedtuple(
    'Label', ['label_value', 'bound', 'attribute', 'context_id'])


class _PseudoLattice(object):
    def is_bottom(self):
        return False

    def is_top(self):
        return False

    def join(self, other):
        if self == other:
            return self
        return Lattice(top=True)


class Label(label_namedtuple_type, _PseudoLattice, Flyweight):
    """Constructs a label for expression or statement `statement`"""
    __slots__ = ()

    def __new__(cls, statement=None, bound=None, attribute=None,
                context_id=None, label_value=None):
        if statement is None and label_value is None:
            raise ValueError(
                'Either statement or label_value must be specified.')
        label_value = label_value or fresh_int(statement)
        return super().__new__(cls, label_value, bound, attribute, context_id)

    def __getnewargs__(self):
        return (
            None, self.bound, self.attribute, self.context_id,
            self.label_value)

    def attributed(self, attribute):
        return self.__class__(
            label_value=self.label_value, bound=self.bound,
            attribute=attribute)

    def attributed_true(self):
        return self.attributed('tt')

    def attributed_false(self):
        return self.attributed('ff')

    def attributed_entry(self):
        return self.attributed('en')

    def attributed_exit(self):
        return self.attributed('ex')

    def signal_name(self):
        return 's_{}'.format(self.label_value)

    def port_name(self):
        return 'p_{}'.format(self.label_value)

    def __str__(self):
        s = 'l{}'.format(self.label_value)
        if self.attribute:
            s += str(self.attribute)
        return s

    def __repr__(self):
        formatter = '{cls}({label!r}, {attribute!r}, {bound!r}, {context!r})'
        return formatter.format(
            cls=self.__class__.__name__, label=self.label_value,
            attribute=self.attribute, bound=self.bound,
            context=self.context_id)


class LabelContext(object):
    def __init__(self, description, out_vars=None):
        super().__init__()
        if not isinstance(description, str):
            description = 'c{}'.format(Label(description).label_value)
        self.description = description
        self.out_vars = out_vars

    def Label(self, statement=None, bound=None, attribute=None):
        lmap = _label_context_maps.setdefault(self.description, {})
        label_value = fresh_int(statement, lmap=lmap)
        return Label(
            label_value=label_value, bound=bound, attribute=attribute,
            context_id=self.description)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.description == other.description

    def __repr__(self):
        return '<{cls}:{description}>'.format(
            cls=self.__class__, description=self.description)


class Identifier(namedtuple('Identifier', ['variable', 'label']), Flyweight):
    __slots__ = ()

    def __new__(cls, variable, label=None):
        label = label or Lattice(bottom=True)
        return super().__new__(cls, variable, label)

    def __str__(self):
        return '{variable}{label}'.format(
            variable=self.variable, label=superscript(self.label))

    def __repr__(self):
        return '{cls}({variable!r}, {label!r})'.format(
            cls=self.__class__.__name__,
            variable=self.variable, label=self.label)


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

s = namedtuple('Statistics', ['dsp', 'ff', 'lut'])
_integer_table = {
    'comparison': s(0, 0, 39),
    operators.ADD_OP: s(0, 0, 32),
    operators.SUBTRACT_OP: s(0, 0, 32),
    operators.MULTIPLY_OP: s(4, 45, 21),
    operators.DIVIDE_OP: s(0, 1712, 1779),
    operators.UNARY_SUBTRACT_OP: s(0, 0, 32),
    operators.TERNARY_SELECT_OP: s(0, 0, 71),
    operators.FIXPOINT_OP: s(0, 0, 0),
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
}


class LabelSemantics(_label_semantics_tuple_type, Flyweight, Comparable):
    """The semantics that captures the area of an expression."""

    def __new__(cls, label, env):
        from soap.semantics.state import MetaState
        return super().__new__(cls, label, MetaState(env))

    def __init__(self, label, env):
        super().__init__()

    @cached
    def luts(self, precision=None):
        """FIXME Emergency luts statistics for now"""
        precision = precision or context.precision
        if precision == 23:
            table = _single_table
        elif precision == 52:
            table = _double_table
        else:
            raise ValueError('Precision must be single (23) or double (52).')

        def accumulate_luts_count(env):
            luts = 0
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
                        luts += _integer_table[op].lut
                    elif datatype is ErrorSemantics:
                        for arg in expr.args:
                            if not isinstance(arg, Label):
                                continue
                            if not isinstance(arg.bound, IntegerInterval):
                                continue
                            if is_numeral(env[arg]):
                                continue
                            conversion_set.add(arg)
                        luts += table[op].lut
                if isinstance(expr, FixExpr):
                    luts += accumulate_luts_count(expr.bool_expr[1])
                    luts += accumulate_luts_count(expr.loop_state)
                    luts += accumulate_luts_count(expr.init_state)
            luts += len(conversion_set) * table['conversion'].lut
            return luts

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

    def __iter__(self):
        return iter((self.label, self.env))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.label == other.label and self.env == other.env

    def __hash__(self):
        return hash((self.__class__, self.label, self.env))

    def __str__(self):
        return '({}, {})'.format(self.label, self.env)
