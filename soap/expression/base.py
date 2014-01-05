"""
.. module:: soap.expression.base
    :synopsis: The base classes of expressions.
"""
from soap.common import Flyweight, cached
from soap.expression.common import expression_factory
from soap.expression.operators import op_func_dict_by_ary_list
from soap.expression.variable import Variable
from soap.label.base import Label
from soap.lattice.flat import FlatLattice


class Expression(FlatLattice, Flyweight):
    """A base class for expressions."""

    __slots__ = ('_op', '_args', '_hash')

    def __init__(self, op=None, *args, top=False, bottom=False):
        super().__init__(top=top, bottom=bottom)
        if top or bottom:
            return
        if not args and not all(args):
            raise ValueError('There is no arguments.')
        self._op = op
        self._args = args

    def _cast_value(self, value, top=False, bottom=False):
        return value

    def __getattr__(self, attribute):
        def raise_err():
            raise AttributeError('{} has no attribute {!r}'.format(
                self.__class__.__name__, attribute))
        if not attribute.startswith('a'):
            raise_err()
        try:
            index = int(attribute[1:]) - 1
            return self.args[index]
        except (ValueError, KeyError):
            raise_err()

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

    @cached
    def eval(self, var_env=None, **kwargs):
        """Recursively evaluates expression using var_env.

        :param var_env: Mapping from variables to values
        :type var_env: Mapping from variables to arbitrary value instances
        :param kwargs: Things to extend our mapping
        :returns: Evaluation result
        """
        from soap.semantics import mpz_type, mpfr_type, mpq_type, Interval

        var_env = var_env.__class__(var_env, **kwargs)

        def eval_arg(a):
            if isinstance(a, Variable):
                return var_env[a]
            if isinstance(a, Expression):
                return a.eval(var_env)
            if isinstance(a, (mpz_type, mpfr_type, mpq_type, Interval)):
                return a
            raise TypeError('Do not know how to evaluate {}'.format(a))

        op_func = op_func_dict_by_ary_list[self.ary - 1][self.op]
        args = list(eval_arg(a) for a in self.args)
        return op_func(*args)

    def exponent_width(self, var_env, prec):
        """Computes the exponent width required for its evaluation so that no
        overflow could occur.

        :param var_env: The ranges of input variables.
        :type var_env: dictionary containing mappings from variables to
            :class:`soap.semantics.error.Interval`
        :param prec: Precision used to evaluate the expression, defaults to
            single precision.
        :type prec: int
        """
        import math
        from soap.semantics.flopoco import we_min
        b = self.error(var_env, prec).v
        bmax = max(abs(b.min), abs(b.max))
        expmax = math.floor(math.log(bmax, 2))
        try:
            we = int(math.ceil(math.log(expmax + 1, 2) + 1))
        except ValueError:
            we = 1
        return max(we, we_min)

    @cached
    def area(self, var_env, prec):
        """Computes the area estimation of its evaulation.

        :param var_env: The ranges of input variables.
        :type var_env: dictionary containing mappings from variables to
            :class:`soap.semantics.error.Interval`
        :param prec: Precision used to evaluate the expression, defaults to
            single precision.
        :type prec: int
        """
        from soap.semantics import AreaSemantics
        return AreaSemantics(self, var_env, prec)

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
        from soap.semantics.flopoco import eval_expr
        return eval_expr(self, var_env, prec)

    @cached
    def error(self, var_env, prec):
        """Computes the error bound of its evaulation.

        :param var_env: The ranges of input variables.
        :type var_env: dictionary containing mappings from variables to
            :class:`soap.semantics.error.Interval`
        :param prec: Precision used to evaluate the expression, defaults to
            single precision.
        :type prec: int
        """
        from soap.semantics import precision_context, BoxState, ErrorSemantics
        with precision_context(prec):
            return ErrorSemantics(self.eval(BoxState(var_env)))

    @cached
    def as_labels(self):
        """Performs labelling analysis on the expression.

        :returns: dictionary containing the labelling scheme.
        """
        def to_label(e):
            try:
                return e.as_labels()
            except AttributeError:
                l = Label(e)
                return l, {l: e}

        args_label, args_env = zip(*(to_label(a) for a in self.args))
        expression = expression_factory(self.op, *args_label)
        label = Label(expression)
        label_env = {label: expression}
        for e in args_env:
            label_env.update(e)
        return label, label_env

    def crop(self, depth):
        """Truncate the tree at a certain depth.

        :param depth: the depth used to truncate the tree.
        :type depth: int
        :returns: the truncated tree and a dictionary containing truncated
            subexpressions.
        """
        def subcrop(a):
            if isinstance(a, Expression):
                return a.crop(depth - 1)
            return a, {}
        if depth > 0:
            args_label, args_env = zip(*(subcrop(a) for a in self.args))
            env = {}
            for e in args_env:
                env.update(e)
            return expression_factory(self.op, *args_label), env
        l = Label(self)
        return l, {l: self}

    def stitch(self, env):
        """Undo truncation by stiching truncated subexpressions back to the
        leaves of the expression.

        :param env: the truncated expressions.
        :type env: dict
        :returns: new expression tree.
        """
        def substitch(a):
            if isinstance(a, Expression):
                return a.stitch(env)
            if isinstance(a, Label):
                return env[a]
            return a
        return self.__class__(self.op, *(substitch(a) for a in self.args))

    def tree(self):
        """Produces a tuple tree for the expression."""
        def to_tuple(a):
            if isinstance(a, Expression):
                return a.tree()
            return a
        return tuple([self.op] + [to_tuple(a) for a in self.args])

    def __iter__(self):
        return iter([self.op] + list(self.args))

    def _args_to_str(self):
        return [(
            '({})' if isinstance(a, Expression) and a.args else '{}').format(a)
            for a in self.args]

    def __repr__(self):
        args = ', '.join('a{}={!r}'.format(i + 1, a)
                         for i, a in enumerate(self.args))
        return "{name}(op={op!r}, {args})".format(
            name=self.__class__.__name__, op=self.op, args=args)

    def _attr(self):
        return (self.op, tuple(self.args))

    def __eq__(self, other):
        if not isinstance(other, Expression):
            return False
        if id(self) == id(other):
            return True
        if hash(self) != hash(other):
            return False
        return self._attr() == other._attr()

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        try:
            return self._hash
        except AttributeError:
            pass
        self._hash = hash(self._attr())
        return self._hash


class UnaryExpression(Expression):
    """A unary expression class. Instance has only one argument."""

    __slots__ = ()

    def __init__(self, op=None, a=None, top=False, bottom=False):
        super().__init__(op, a, top=top, bottom=bottom)

    @property
    def a(self):
        return self.args[0]

    def __str__(self):
        return '{op}{a}'.format(op=self.op, a=self._args_to_str().pop())


class BinaryExpression(Expression):
    """A binary expression class. Instance has two arguments."""

    __slots__ = ()

    def __init__(self, op=None, a1=None, a2=None, top=False, bottom=False):
        super().__init__(op, a1, a2, top=top, bottom=bottom)

    def __str__(self):
        a1, a2 = self._args_to_str()
        return '{a1} {op} {a2}'.format(op=self.op, a1=a1, a2=a2)


class TernaryExpression(Expression):
    """A ternary expression class. Instance has three arguments."""

    __slots__ = ()

    def __init__(self, op=None, a1=None, a2=None, a3=None,
                 top=False, bottom=False):
        super().__init__(op, a1, a2, a3, top=top, bottom=bottom)
