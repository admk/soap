"""
.. module:: soap.expression.base
    :synopsis: The base classes of expressions.
"""
from soap.common import Comparable, Flyweight, Label, cached
from soap.expression.common import (
    expression_factory, op_func_dict_by_ary_list, COMMUTATIVITY_OPERATORS
)
from soap.expression.variable import Variable


class Expression(Flyweight, Comparable):
    """A base class for expressions."""

    __slots__ = ('op', 'args', '_hash')

    def __init__(self, op, *args):
        if not args:
            raise ValueError('There is no arguments.')
        super().__setattr__('op', op)
        super().__setattr__('args', args)

    def __getattribute__(self, attribute):
        if attribute[0] != 'a':
            return super().__getattribute__(attribute)
        try:
            index = int(attribute[1:]) - 1
        except ValueError:
            return super().__getattribute__(attribute)
        try:
            return self.args[index]
        except KeyError:
            raise AttributeError(
                '{} has no attribute at index {}'.format(
                    self.__class__.__name__, index))

    def __setattribute__(self, *_):
        raise NotImplementedError
    __delattribute__ = __setattribute__

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
        # FIXME regression: integer intervals won't produce errors.
        from soap.semantics import precision_context, BoxState
        with precision_context(prec):
            return self.eval(BoxState(var_env))

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

    def _sort_attr(self):
        args = list(self.args)
        if self.op in COMMUTATIVITY_OPERATORS:
            args = sorted(args)
        return tuple([self.op] + args)

    def __eq__(self, other):
        if not isinstance(other, Expression):
            return False
        if id(self) == id(other):
            return True
        return self._sort_attr() == other._sort_attr()

    def __lt__(self, other):
        if not isinstance(other, Expression):
            return False
        return self._sort_attr() < other._sort_attr()

    def __hash__(self):
        try:
            return self._hash
        except AttributeError:
            pass
        self._hash = hash(self._sort_attr())
        return self._hash


class UnaryExpression(Expression):
    """A unary expression class. Instance has only one argument."""

    __slots__ = ()

    def __init__(self, op, a):
        super().__init__(op, a)

    @property
    def a(self):
        return self.args[0]

    def __str__(self):
        return '{op}{a}'.format(op=self.op, a=self._args_to_str().pop())


class BinaryExpression(Expression):
    """A binary expression class. Instance has two arguments."""

    __slots__ = ()

    def __init__(self, op, a1, a2):
        super().__init__(op, a1, a2)

    def __str__(self):
        a1, a2 = self._args_to_str()
        return '{a1} {op} {a2}'.format(op=self.op, a1=a1, a2=a2)


class TernaryExpression(Expression):
    """A ternary expression class. Instance has three arguments."""

    __slots__ = ()

    def __init__(self, op, a1, a2, a3):
        super().__init__(op, a1, a2, a3)
