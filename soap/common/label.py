from reprlib import recursive_repr

from soap.common.cache import Flyweight
from soap.lattice.base import Lattice
from soap.lattice.flat import flat, denotational


_label_count = 0
_label_map = None


def fresh_int(e=None):
    """Generates a fresh int for the label of the expression `e`."""
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


class Label(flat(int), Flyweight):
    """Constructs a label for expression or statement `statement`"""
    __slots__ = ('label_value', 'statement', 'description')

    def __init__(self, statement=None, label_value=None, description=None,
                 top=False, bottom=False):
        self.label_value = label_value or fresh_int(
            (statement, self.__class__))
        self.statement = statement
        self.description = description
        super().__init__(top=top, bottom=bottom, value=self.label_value)

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
        s = 'l{}'.format(self.label_value)
        if self.description:
            s += ':{.desc}'.format(self)
        return s

    @recursive_repr()
    def __repr__(self):
        return '{cls}({label!r}, {statement!r})'.format(
            cls=self.__class__.__name__,
            label=self.label_value, statement=self.statement)

    def __eq__(self, other):
        if not isinstance(other, Label):
            return False
        return self.label_value == other.label_value

    def __hash__(self):
        return hash((self.__class__, self.label_value))


class Iteration(denotational(int)):
    pass


class Identifier(Lattice):

    class Annotation(Label * Iteration):
        __slots__ = ('label', 'iteration')

        def __init__(self, label=None, iteration=None):
            self.label = label or Label(bottom=True)
            self.iteration = iteration or Iteration(bottom=True)
            super().__init__(self_obj=label, other_obj=iteration)

    __slots__ = ('name', 'annotation')

    def __init__(self, variable, label=None, iteration=None):
        self.variable = variable
        self.annotation = self.Annotation(label=label, iteration=iteration)

    def __str__(self):
        return '({variable}, {label}, {iteration})'.format(
            variable=self.variable,
            label=self.annotation.label, iteration=self.annotation.iteration)

    def __repr__(self):
        return '{cls}({variable!r}, {label!r}, {iteration!r})'.format(
            cls=self.__class__.__name__, variable=self.variable,
            label=self.annotation.label, iteration=self.annotation.iteration)
