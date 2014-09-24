"""
.. module:: soap.expression.variable
    :synopsis: The class of variables.
"""
import collections

from soap.expression.base import Expression, UnaryExpression
from soap.expression.arithmetic import ArithmeticMixin
from soap.expression.boolean import BooleanMixin


class Variable(ArithmeticMixin, BooleanMixin, UnaryExpression):
    """The variable class."""

    __slots__ = ()

    def __init__(self, name=None, top=False, bottom=False):
        super().__init__(op=None, a=name, top=top, bottom=bottom)

    @property
    def name(self):
        return self.args[0]

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return '{cls}({name!r})'.format(
            cls=self.__class__.__name__, name=self.name)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.name == other.name

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        self._hash = hash_val = hash((self.name))
        return hash_val


class _MagicalMixin(object):
    pass


class InputVariable(_MagicalMixin, Variable):
    pass


class OutputVariable(_MagicalMixin, Variable):
    pass


class External(_MagicalMixin, ArithmeticMixin, BooleanMixin, Expression):
    def __init__(self, var, top=False, bottom=False):
        super().__init__(None, var, top=top, bottom=bottom)

    @property
    def var(self):
        return self.args[0]

    def __str__(self):
        return '^{}'.format(self.var)


class VariableTuple(
        _MagicalMixin, collections.Sequence, ArithmeticMixin, BooleanMixin,
        Expression):
    """Tuple of variables. """

    def __init__(self, *args, top=False, bottom=False):
        if len(args) == 1:
            args0 = args[0]
            if isinstance(args0, collections.Iterable):
                args = args0
        # flatten variable tuples
        flat_args = []
        for v in args:
            if isinstance(v, self.__class__):
                flat_args += v
            else:
                flat_args.append(v)
        super().__init__(None, *flat_args, top=top, bottom=bottom)

    def __getitem__(self, index):
        return self.args[index]

    def __len__(self):
        return len(self.args)

    def __str__(self):
        var_list = ','.join(str(v) for v in self.args)
        return '({})'.format(var_list)

    def __repr__(self):
        return '{cls}({name!r})'.format(
            cls=self.__class__.__name__, name=self.args)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.args == other.args

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self.args, self.__class__))


class InputVariableTuple(VariableTuple):
    pass


class OutputVariableTuple(VariableTuple):
    pass
