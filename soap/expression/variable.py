"""
.. module:: soap.expression.variable
    :synopsis: The class of variables.
"""
import collections

from soap.datatype import auto_type
from soap.expression.arithmetic import ArithmeticMixin
from soap.expression.base import Expression, BinaryExpression
from soap.expression.boolean import BooleanMixin
from soap.expression.operators import EXTERNAL_OP, VARIABLE_OP


class Variable(ArithmeticMixin, BooleanMixin, BinaryExpression):
    """The variable class."""

    __slots__ = ()

    def __init__(self, name, dtype=auto_type):
        super().__init__(VARIABLE_OP, name, dtype)

    @property
    def name(self):
        return self.args[0]

    @property
    def dtype(self):
        return self.args[1]

    def format(self):
        return '{}'.format(self.name)

    def __repr__(self):
        return '{cls}({name!r}, {dtype!r})'.format(
            cls=self.__class__.__name__, name=self.name, dtype=self.dtype)


class InputVariable(Variable):
    pass


class OutputVariable(Variable):
    pass


class External(ArithmeticMixin, BooleanMixin, Expression):
    def __init__(self, var):
        super().__init__(EXTERNAL_OP, var)

    @property
    def var(self):
        return self.args[0]

    def format(self):
        return '^{}'.format(self.var)


class VariableTuple(ArithmeticMixin, BooleanMixin, Expression):
    """Tuple of variables. """

    def __init__(self, *args):
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
        super().__init__(None, *flat_args)

    def __getitem__(self, index):
        return self.args[index]

    def __len__(self):
        return len(self.args)

    def format(self):
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
