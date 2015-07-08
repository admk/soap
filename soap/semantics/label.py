from collections import namedtuple

from soap.common import Comparable, Flyweight
from soap.datatype import type_of


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
    _str_brackets = False

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

    def format(self):
        s = 'l{}({})'.format(self.label_value, self.bound)
        s = 'l{}'.format(self.label_value)
        return s

    def __eq__(self, other):
        return (self.__class__ == other.__class__ and
                self.label_value == other.label_value)

    def __hash__(self):
        return hash((self.__class__, self.label_value))

    def __str__(self):
        return self.format()

    def __repr__(self):
        formatter = '{cls}({label!r}, {bound!r}, {invariant!r}, {context!r})'
        return formatter.format(
            cls=self.__class__.__name__, label=self.label_value,
            bound=self.bound, invariant=self.invariant,
            context=self.context_id)


class LabelContext(object):
    label_class = Label

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
        return self.label_class(
            statement, bound=bound, invariant=invariant,
            context_id=self.description, _label_value=label_value)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.description == other.description

    def __repr__(self):
        return '<{cls}:{description}>'.format(
            cls=self.__class__, description=self.description)


_label_semantics_tuple_type = namedtuple('LabelSemantics', ['label', 'env'])


class LabelSemantics(_label_semantics_tuple_type, Flyweight, Comparable):
    """The semantics that captures the area of an expression."""
    def __new__(cls, label, env):
        from soap.semantics.state import MetaState
        if not isinstance(env, MetaState):
            env = MetaState(env)
        return super().__new__(cls, label, env)

    def resources(self):
        from soap.semantics.resource import resource_count
        return resource_count(self)

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
