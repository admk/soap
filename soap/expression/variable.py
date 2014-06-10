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
        return self.a

    def vars(self):
        return {self}

    def eval(self, state):
        return state[self]

    def label(self, context=None):
        from soap.label.base import LabelContext
        from soap.semantics.label import LabelSemantics

        context = context or LabelContext(self)

        label = context.Label(self)
        env = {label: self}

        return LabelSemantics(label, env)

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
        return hash((self.name, self.__class__))


class InputVariable(Variable):
    pass


class OutputVariable(Variable):
    pass


class _MagicalMixin(object):

    def vars(self):
        raise RuntimeError(
            '_MagicalMixin expressions has no local dependencies.')

    def eval(self, state):
        raise RuntimeError('Not suitable for arithmetic evaluation.')

    def label(self, context=None):
        raise RuntimeError('Not suitable for labelling.')


class External(_MagicalMixin, ArithmeticMixin, BooleanMixin, Expression):
    def __init__(self, var, top=False, bottom=False):
        if isinstance(var, Variable):
            # because a label is always unique, and a variable could change
            raise TypeError('External must take a label, not a variable')
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
