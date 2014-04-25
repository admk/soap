from reprlib import recursive_repr

from soap import logger
from soap.common.cache import Flyweight
from soap.lattice.flat import flat


_label_map = {}


class _Dummy(object):
    def __hash__(self):
        return id(self)


def fresh_int(statement=None, lmap=_label_map):
    """
    Generates a fresh int for the label of `statement`, within the known
    label mapping `lmap`.
    """
    if statement is None:
        logger.error('Trying to get a fresh unassociated label. Reason?')
        statement = _Dummy()
    return lmap.setdefault(statement, len(lmap) + 1)


class Label(flat(tuple), Flyweight):
    """Constructs a label for expression or statement `statement`"""
    __slots__ = ()

    def __init__(self, statement=None, attribute=None,
                 context_id=None, label_value=None,
                 top=False, bottom=False):
        if top or bottom:
            # to avoid extraneous labels
            super().__init__(top=top, bottom=bottom)
            return
        label_value = label_value or fresh_int(statement=statement)
        value = (label_value, attribute, context_id)
        super().__init__(value=value, top=top, bottom=bottom)

    @property
    def label_value(self):
        return self.value[0]

    @property
    def attribute(self):
        return self.value[1]

    @property
    def context_id(self):
        return self.value[2]

    def attributed(self, attribute):
        if self.is_top() or self.is_bottom():
            raise ValueError(
                'Top or bottom label cannot be assigned attribute.')
        return self.__class__(
            label_value=self.label_value, attribute=attribute)

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
            s += '{}'.format(self.attribute)
        return s

    @recursive_repr()
    def __repr__(self):
        return '{cls}({label!r})'.format(
            cls=self.__class__.__name__, label=self.label_value,
            attribute=self.attribute, context=self.context_id)


class LabelContext(object):
    def __init__(self, description):
        if not isinstance(description, str):
            description = Label(description)
        self.description = description
        self.lmap = {}

    def Label(self, statement=None, attribute=None, top=False, bottom=False):
        label_value = fresh_int(statement=statement, lmap=self.lmap)
        return Label(
            label_value=label_value, attribute=attribute,
            context_id=self.description)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.description == other.description

    def __repr__(self):
        return '<{cls}:{description}>'.format(
            cls=self.__class__, description=self.description)
