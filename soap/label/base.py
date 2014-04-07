from reprlib import recursive_repr

from soap.common.cache import Flyweight
from soap.lattice.flat import flat


_label_count = 0
_label_map = None


def fresh_int(e=None):
    """Generates a fresh int for the label of the expression `e`.

    if the expression `e` is None, always return a new integer.
    """
    def _incr():
        global _label_count
        _label_count += 1
        return _label_count
    global _label_map
    _label_map = _label_map or {}
    if e is not None and e in _label_map:
        return _label_map[e]
    l = _incr()
    if e is not None:
        _label_map[e] = l
    return l


class Label(flat(tuple), Flyweight):
    """Constructs a label for expression or statement `statement`"""
    __slots__ = ('label_value', 'statement', 'attribute', 'description')

    def __init__(self, statement=None, attribute=None, label_value=None,
                 description=None, top=False, bottom=False):
        if top or bottom:
            # to avoid extraneous labels
            super().__init__(top=top, bottom=bottom)
            return
        self.label_value = label_value or fresh_int(statement)
        self.statement = statement
        self.attribute = attribute
        self.description = description
        value = (self.label_value, self.attribute)
        super().__init__(top=top, bottom=bottom, value=value)

    def attributed(self, attribute):
        if self.is_top() or self.is_bottom():
            raise ValueError(
                'Top or bottom label cannot be assigned attribute.')
        return self.__class__(
            statement=self.statement, attribute=attribute,
            description=self.description)

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
        from soap.expression.operators import OPERATORS
        forbidden = OPERATORS + [',', '(', ')', '[', ']']
        if any(k in str(self.e) for k in forbidden):
            s = self.label_value
        else:
            s = self.statement
        return 'p_{}'.format(s)

    def __str__(self):
        s = '{}'.format(self.label_value)
        if self.attribute:
            s += '{}'.format(self.attribute)
        if self.description:
            s += ':{.desc}'.format(self)
        return s

    @recursive_repr()
    def __repr__(self):
        return '{cls}({label!r}, {statement!r}, {attribute!r})'.format(
            cls=self.__class__.__name__, label=self.label_value,
            statement=self.statement, attribute=self.attribute)
