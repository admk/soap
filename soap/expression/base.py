"""
.. module:: soap.expression.base
    :synopsis: The base classes of expressions.
"""
from soap.common import Flyweight, cached, base_dispatcher
from soap.expression.common import is_expression
from soap.lattice.base import Lattice
from soap.lattice.flat import FlatLattice


class Expression(FlatLattice, Flyweight):
    """A base class for expressions."""

    __slots__ = ('_op', '_args')

    def __init__(self, op=None, *args, top=False, bottom=False, **kwargs):
        super().__init__(top=top, bottom=bottom)
        if top or bottom:
            return
        if not args and not all(args):
            raise ValueError('There is no arguments.')
        self._op = op
        self._args = args

    def _cast_value(self, value, top=False, bottom=False):
        return value

    @property
    def op(self):
        return self._op

    @property
    def args(self):
        return self._args

    @property
    def ary(self):
        return len(self.args)

    def is_n_ary(self, n):
        return self.ary == n

    def is_unary(self):
        return self.is_n_ary(1)

    def is_binary(self):
        return self.is_n_ary(2)

    def is_ternary(self):
        return self.is_n_ary(3)

    def vars(self):
        return expression_variables(self)

    @cached
    def luts(self, var_env, prec):
        """Computes the area estimation of its evaulation.

        :param var_env: The ranges of input variables.
        :type var_env: dictionary containing mappings from variables to
            :class:`soap.semantics.error.Interval`
        :param prec: Precision used to evaluate the expression, defaults to
            single precision.
        :type prec: int
        """
        return self.label().luts()

    @cached
    def real_area(self, var_env, prec):
        """Computes the actual area by synthesising it using XST with flopoco
        cores.

        :param var_env: The ranges of input variables.
        :type var_env: dictionary containing mappings from variables to
            :class:`soap.semantics.error.Interval`
        :param prec: Precision used to evaluate the expression, defaults to
            single precision.
        :type prec: int
        """
        from soap.flopoco.actual import actual_luts
        return actual_luts(self, var_env, prec)

    def __iter__(self):
        return iter([self.op] + list(self.args))

    def _args_to_str(self):
        from soap.expression.arithmetic import UnaryArithExpr

        def format(expr):
            if isinstance(expr, Lattice) and expr.is_bottom():
                brackets = False
            elif isinstance(expr, UnaryArithExpr):
                brackets = False
            else:
                brackets = is_expression(expr) and expr.args
            text = '({})' if brackets else '{}'
            return text.format(expr)

        return [format(a) for a in self.args]

    def __repr__(self):
        args = ', '.join('a{}={!r}'.format(i + 1, a)
                         for i, a in enumerate(self.args))
        return "{name}(op={op!r}, {args})".format(
            name=self.__class__.__name__, op=self.op, args=args)

    def __str__(self):
        raise NotImplementedError

    def _attr(self):
        return (self.op, tuple(self.args))

    def __eq__(self, other):
        if not isinstance(other, Expression):
            return False
        if id(self) == id(other):
            return True
        if hash(self) != hash(other) or type(self) is not type(other):
            return False
        return self._attr() == other._attr()

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        self._hash = hash_val = hash(self._attr())
        return hash_val


class UnaryExpression(Expression):
    """A unary expression class. Instance has only one argument."""

    __slots__ = ()

    def __init__(self, op=None, a=None, top=False, bottom=False, **kwargs):
        super().__init__(op, a, top=top, bottom=bottom, **kwargs)

    @property
    def a(self):
        return self.args[0]

    @property
    def a1(self):
        return self.args[0]

    def __str__(self):
        return '{op}{a}'.format(op=self.op, a=self._args_to_str().pop())


class BinaryExpression(Expression):
    """A binary expression class. Instance has two arguments."""

    __slots__ = ()

    def __init__(self, op=None, a1=None, a2=None, top=False, bottom=False,
                 **kwargs):
        super().__init__(op, a1, a2, top=top, bottom=bottom, **kwargs)

    @property
    def a1(self):
        return self.args[0]

    @property
    def a2(self):
        return self.args[1]

    def __str__(self):
        a1, a2 = self._args_to_str()
        return '{a1} {op} {a2}'.format(op=self.op, a1=a1, a2=a2)


class TernaryExpression(Expression):
    """A ternary expression class. Instance has three arguments."""

    __slots__ = ()

    def __init__(self, op=None, a1=None, a2=None, a3=None,
                 top=False, bottom=False, **kwargs):
        super().__init__(op, a1, a2, a3, top=top, bottom=bottom, **kwargs)

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

    def __init__(self, op=None, a1=None, a2=None, a3=None, a4=None,
                 top=False, bottom=False, **kwargs):
        super().__init__(op, a1, a2, a3, a4, top=top, bottom=bottom, **kwargs)

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


class VariableSetGenerator(base_dispatcher()):

    def generic_execute(self, expr):
        raise TypeError(
            'Do not know how to find input variables for {!r}'.format(expr))

    def _execute_atom(self, expr):
        return {expr}

    def _execute_expression(self, expr):
        input_vars = set()
        for arg in expr.args:
            input_vars |= self(arg)
        return input_vars

    def execute_tuple(self, expr):
        return set(expr)

    def execute_numeral(self, expr):
        return set()

    def execute_FixExpr(self, expr):
        input_vars = set()
        for expr in expr.init_state.values():
            input_vars |= self(expr)
        return input_vars

    execute_Label = _execute_atom
    execute_Variable = _execute_atom
    execute_UnaryArithExpr = execute_BinaryArithExpr = _execute_expression
    execute_BinaryBoolExpr = _execute_expression
    execute_SelectExpr = _execute_expression


expression_variables = VariableSetGenerator()
