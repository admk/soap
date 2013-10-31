"""
.. module:: soap.expression.arithmetic
    :synopsis: The class of expressions.
"""
from soap.common import Comparable, Flyweight, cached
from soap.expression.common import (
    ADD_OP, SUBTRACT_OP, MULTIPLY_OP, DIVIDE_OP, UNARY_SUBTRACT_OP,
    LESS_OP, LESS_EQUAL_OP, EQUAL_OP, GREATER_EQUAL_OP, GREATER_OP,
    BARRIER_OP, COMMUTATIVITY_OPERATORS, UNARY_OPERATORS
)
from soap.expression.variable import Var
from soap.expression.parser import parse


_binary_op_func_dict = {
    ADD_OP: lambda x, y: x + y,
    SUBTRACT_OP: lambda x, y: x - y,
    MULTIPLY_OP: lambda x, y: x * y,
    DIVIDE_OP: lambda x, y: x / y,
    LESS_OP: lambda x, y: x < y,
    LESS_EQUAL_OP: lambda x, y: x <= y,
    EQUAL_OP: lambda x, y: x == y,
    GREATER_EQUAL_OP: lambda x, y: x >= y,
    GREATER_OP: lambda x, y: x > y,
}

_unary_op_func_dict = {
    UNARY_SUBTRACT_OP: lambda x, _: -x,
}


class Expr(Comparable, Flyweight):
    """The expression class."""

    __slots__ = ('op', 'a1', 'a2', '_hash')

    def __init__(self, *args, **kwargs):
        """Expr allows several ways of instantiation for the expression example
        ``(a + b)``::

            1. ``Expr('+', 'a', 'b')``
            2. ``Expr(op='+', a1='a', a2='b')``
            3. ``Expr(op='+', al=('a', 'b'))``

        Expr also allows unary operations, for example for ``a``::

            1. ``Expr('-', 'a')``
            2. ``Expr('-', 'a', None)``
            3. ``Expr(op='-', a='a')``
            4. ``Expr(op='-', al=['a'])``
        """
        if kwargs:
            op = kwargs.setdefault('op')
            a1 = kwargs.setdefault('a1')
            a2 = kwargs.setdefault('a2')
            if a1 is not None and a2 is not None:
                al = a1, a2
            else:
                al = kwargs.setdefault('al') or [kwargs.setdefault('a')]
        elif len(args) == 1:
            e = list(args).pop()
            try:
                op, al = e.op, e.args
            except AttributeError:
                e = parse(e)
            try:
                op, al = e.op, e.args
            except AttributeError:
                raise ValueError('String is not an expression')
        elif len(args) == 2:
            op, al = args
            if op in UNARY_OPERATORS:
                al = [al]
        elif len(args) == 3:
            op, *al = args
        self.op = op
        al = list(al)
        self.a1 = al.pop(0)
        self.a2 = al.pop(0) if al else None
        super().__init__()

    def __getnewargs__(self):
        return self.op, self.a1, self.a2

    @property
    def a(self):
        if self.is_unary():
            return self.a1
        raise AttributeError('A binary expression has no attribute "a"')

    def is_unary(self):
        return (self.op in UNARY_OPERATORS) and (self.a2 is None)

    def is_binary(self):
        return not self.is_unary()

    def tree(self):
        """Produces a tuple tree for the expression."""
        def to_tuple(a):
            if isinstance(a, Expr):
                return a.tree()
            return a
        return (self.op, to_tuple(self.a1), to_tuple(self.a2))

    @property
    def args(self):
        """Returns the arguments of the expression"""
        if self.a2 is not None:
            return [self.a1, self.a2]
        return [self.a1]

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
            if isinstance(a, Var):
                return var_env[a]
            if isinstance(a, Expr):
                return a.eval(var_env)
            if isinstance(a, (mpz_type, mpfr_type, mpq_type, Interval)):
                return a
            raise TypeError('Do not know how to evaluate {}'.format(a))

        if self.is_unary():
            op_func = _unary_op_func_dict[self.op]
            args = [eval_arg(self.a1)]
        else:
            op_func = _binary_op_func_dict[self.op]
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
    def as_labels(self):
        """Performs labelling analysis on the expression.

        :returns: dictionary containing the labelling scheme.
        """
        from soap.common import Label

        def to_label(e):
            try:
                return e.as_labels()
            except AttributeError:
                l = Label(e)
                return l, {l: e}

        l1, s1 = to_label(self.a1)
        l2, s2 = to_label(self.a2)
        e = Expr(op=self.op, a1=l1, a2=l2)
        l = Label(e)
        s = {l: e}
        s.update(s1)
        s.update(s2)
        return l, s

    def crop(self, depth):
        """Truncate the tree at a certain depth.

        :param depth: the depth used to truncate the tree.
        :type depth: int
        :returns: the truncated tree and a dictionary containing truncated
            subexpressions.
        """
        def subcrop(a):
            try:
                return a.crop(depth - 1)
            except AttributeError:
                return a, {}
        if depth > 0:
            l1, s1 = subcrop(self.a1)
            l2, s2 = subcrop(self.a2)
            s1.update(s2)
            return self.__class__(self.op, l1, l2), s1
        from soap.common import Label
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
            try:
                return a.stitch(env)
            except AttributeError:
                pass
            try:
                return env[a]
            except KeyError:
                return a
        return self.__class__(self.op, substitch(self.a1), substitch(self.a2))

    def __iter__(self):
        return iter((self.op, self.a1, self.a2))

    def __str__(self):
        a1, a2 = [('({})' if isinstance(a, Expr) else '{}').format(a)
                  for a in (self.a1, self.a2)]
        if self.op in COMMUTATIVITY_OPERATORS:
            a1, a2 = sorted((a1, a2))
        if self.is_unary():
            return '{op}{a}'.format(op=self.op, a=a1)
        return '{a1} {op} {a2}'.format(op=self.op, a1=a1, a2=a2)

    def __repr__(self):
        return "%s(op='%s', a1=%s, a2=%s)" % \
            (self.__class__.__name__, self.op, repr(self.a1), repr(self.a2))

    def __add__(self, other):
        return Expr(op=ADD_OP, a1=self, a2=other)

    def __sub__(self, other):
        return Expr(op=SUBTRACT_OP, a1=self, a2=other)

    def __mul__(self, other):
        return Expr(op=MULTIPLY_OP, a1=self, a2=other)

    def __div__(self, other):
        return Expr(op=DIVIDE_OP, a1=self, a2=other)

    def __floordiv__(self, other):
        return Expr(op=BARRIER_OP, a1=self, a2=other)

    def __neg__(self):
        return Expr(op=UNARY_SUBTRACT_OP, a=self)

    def _symmetric_id(self):
        if self.op in COMMUTATIVITY_OPERATORS:
            _sym_id = (self.op, frozenset(self.args))
        else:
            _sym_id = tuple(self)
        return _sym_id

    def __eq__(self, other):
        if not isinstance(other, Expr):
            return False
        if self.op != other.op:
            return False
        if id(self) == id(other):
            return True
        return self._symmetric_id() == other._symmetric_id()

    def __lt__(self, other):
        if not isinstance(other, Expr):
            return False
        return self._symmetric_id() < other._symmetric_id()

    def __hash__(self):
        try:
            return self._hash
        except AttributeError:
            pass
        self._hash = hash(self._symmetric_id())
        return self._hash
