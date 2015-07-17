"""
.. module:: soap.expression.base
    :synopsis: The base classes of expressions.
"""
from soap.common import Flyweight
from soap.expression.common import is_expression, expression_variables
from soap.semantics import is_numeral


class Expression(Flyweight):
    """A base class for expressions."""

    __slots__ = ('_op', '_args', '_hash')
    _str_brackets = True

    def __init__(self, op, *args):
        super().__init__()
        if not args and not all(args):
            raise ValueError('There is no arguments.')
        self._op = op
        self._args = args
        self._hash = None

    def __setstate__(self, state):
        self._hash = None
        state = state[1]
        self._op = state['_op']
        self._args = state['_args']

    @property
    def op(self):
        return self._op

    @property
    def args(self):
        return self._args

    @property
    def arity(self):
        return len(self.args)

    def vars(self):
        return expression_variables(self)

    def _args_to_str(self):
        def format(expr):
            if is_numeral(expr):
                brackets = False
            else:
                brackets = getattr(expr, '_str_brackets', True)
            if is_expression(expr):
                expr = expr.format()
            text = '({})' if brackets else '{}'
            return text.format(expr)
        return [format(a) for a in self.args]

    def __repr__(self):
        args = ', '.join('a{}={!r}'.format(i + 1, a)
                         for i, a in enumerate(self.args))
        return "{name}(op={op!r}, {args})".format(
            name=self.__class__.__name__, op=self.op, args=args)

    def format(self):
        raise NotImplementedError(
            'Override this method for {}'.format(self.__class__))

    def __str__(self):
        return self.format().replace('    ', '').replace('\n', '').strip()

    def _attr(self):
        return (self.op, self.args)

    def __eq__(self, other):
        if not isinstance(other, Expression):
            return False
        if id(self) == id(other):
            return True
        if type(self) is not type(other) or hash(self) != hash(other):
            return False
        return self._attr() == other._attr()

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        if self._hash:
            return self._hash
        self._hash = hash(self._attr())
        return self._hash


class UnaryExpression(Expression):
    """A unary expression class. Instance has only one argument."""

    __slots__ = ()

    def __init__(self, op, a):
        super().__init__(op, a)

    @property
    def a(self):
        return self.args[0]

    @property
    def a1(self):
        return self.args[0]

    def format(self):
        return '{op}{a}'.format(op=self.op, a=self._args_to_str().pop())


class BinaryExpression(Expression):
    """A binary expression class. Instance has two arguments."""

    __slots__ = ()

    def __init__(self, op, a1, a2):
        super().__init__(op, a1, a2)

    @property
    def a1(self):
        return self.args[0]

    @property
    def a2(self):
        return self.args[1]

    def format(self):
        a1, a2 = self._args_to_str()
        return '{a1} {op} {a2}'.format(op=self.op, a1=a1, a2=a2)


class TernaryExpression(Expression):
    """A ternary expression class. Instance has three arguments."""

    __slots__ = ()

    def __init__(self, op, a1, a2, a3):
        super().__init__(op, a1, a2, a3)

    @property
    def a1(self):
        return self.args[0]

    @property
    def a2(self):
        return self.args[1]

    @property
    def a3(self):
        return self.args[2]


class QuaternaryExpression(Expression):
    """A quaternary expression class. Instance has four arguments."""

    __slots__ = ()

    def __init__(self, op, a1, a2, a3, a4):
        super().__init__(op, a1, a2, a3, a4)

    @property
    def a1(self):
        return self.args[0]

    @property
    def a2(self):
        return self.args[1]

    @property
    def a3(self):
        return self.args[2]

    @property
    def a4(self):
        return self.args[3]
