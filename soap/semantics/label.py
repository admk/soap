from collections import namedtuple
import math

from soap import flopoco
from soap.common import Comparable, Flyweight, superscript
from soap.expression import (
    External, FixExpr, is_expression, OutputVariableTuple
)
from soap.expression.operators import (
    FIXPOINT_OP, TERNARY_SELECT_OP, TRADITIONAL_OPERATORS
)
from soap.lattice.base import Lattice
from soap.semantics.error import IntegerInterval, ErrorSemantics


_label_map = {}


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
        if not isinstance(description, str):
            description = 'c{}'.format(Label(description).label_value)
        self.description = description
        self.out_vars = out_vars
        self.lmap = {}

    def Label(self, statement=None, bound=None, attribute=None):
        label_value = fresh_int(statement, lmap=self.lmap)
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


_FILTER_OPERATORS = TRADITIONAL_OPERATORS + [TERNARY_SELECT_OP]


def _datatype_exponent(op, label):
    if isinstance(label, OutputVariableTuple):
        exponent = 0
        for l in label:
            label_datatype, label_exponent = _datatype_exponent(op, l)
            exponent += label_exponent
        return None, exponent

    if op == FIXPOINT_OP:
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


class LabelSemantics(_label_semantics_tuple_type, Flyweight, Comparable):
    """The semantics that captures the area of an expression."""

    def __new__(cls, label, env):
        from soap.semantics.state import MetaState
        return super().__new__(cls, label, MetaState(env))

    def __init__(self, label, env):
        super().__init__()
        self._luts = None

    def luts(self, precision):
        if self._luts is not None:
            return self._luts

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

        self._luts = accumulate_luts_count(self.env)
        return self._luts

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
