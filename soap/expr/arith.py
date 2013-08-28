"""
.. module:: soap.expr.arith
    :synopsis: The class of expressions.
"""
import gmpy2

from soap.common import Comparable, Flyweight, cached, ignored
from soap.expr.common import (
    ADD_OP, MULTIPLY_OP, BARRIER_OP, COMMUTATIVITY_OPERATORS
)
from soap.expr.parser import parse


class Expr(Comparable, Flyweight):
    """The expression class."""

    __slots__ = ('op', 'a1', 'a2', '_hash')

    def __init__(self, *args, **kwargs):
        """Expr allows several ways of instantiation for the expression example
        (a + b)::

            1. ``Expr('+', a, b)``
            2. ``Expr(op='+', a1=a, a2=b)``
            3. ``Expr('+', al=(a, b))``
        """
        if kwargs:
            op = kwargs.setdefault('op')
            a1 = kwargs.setdefault('a1')
            a2 = kwargs.setdefault('a2')
            al = a1, a2
        if len(args) == 1:
            expr = list(args).pop()
            try:
                op, al = expr.op, expr.args
            except AttributeError:
                expr = parse(expr, self.__class__)
            try:
                op, al = expr.op, expr.args
            except AttributeError:
                raise ValueError('String is not an expression')
        elif len(args) == 2:
            op, al = args
        elif len(args) == 3:
            op, *al = args
        self.op = op
        self.a1, self.a2 = al
        super().__init__()

    def __getnewargs__(self):
        return self.op, self.a1, self.a2

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
        return [self.a1, self.a2]

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
        from soap.semantics import (
            cast_error, cast_error_constant, precision_context
        )
        with precision_context(prec):
            def eval(a):
                with ignored(AttributeError):
                    return a.error(var_env, prec)
                with ignored(TypeError, KeyError):
                    return eval(var_env[a])
                with ignored(TypeError):
                    return cast_error(*a)
                with ignored(TypeError):
                    return cast_error_constant(a)
                return a
            e1, e2 = eval(self.a1), eval(self.a2)
            if self.op == ADD_OP:
                return e1 + e2
            if self.op == MULTIPLY_OP:
                return e1 * e2
            if self.op == BARRIER_OP:
                return e1 | e2

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
        from soap.semantics import Label

        def to_label(e):
            try:
                return e.as_labels()
            except AttributeError:
                l = Label(e)
                return l, {l: e}

        l1, s1 = to_label(self.a1)
        l2, s2 = to_label(self.a2)
        e = BExpr(op=self.op, a1=l1, a2=l2)
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
        from soap.semantics import Label
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
        a1, a2 = sorted([str(self.a1), str(self.a2)])
        return '(%s %s %s)' % (a1, self.op, a2)

    def __repr__(self):
        return self.__str__()
        return "Expr(op='%s', a1=%s, a2=%s)" % \
            (self.op, repr(self.a1), repr(self.a2))

    def __add__(self, other):
        return Expr(op=ADD_OP, a1=self, a2=other)

    def __mul__(self, other):
        return Expr(op=MULTIPLY_OP, a1=self, a2=other)

    def __or__(self, other):
        return Expr(op=BARRIER_OP, a1=self, a2=other)

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


class BExpr(Expr):
    """An expression class that only allows non-expression arguments.

    This is a subclass of :class:`Expr`.
    """

    __slots__ = Expr.__slots__

    def __init__(self, **kwargs):
        from soap.semantics import Label
        super().__init__(**kwargs)
        if not isinstance(self.a1, Label) or not isinstance(self.a2, Label):
            raise ValueError('BExpr allows only binary expressions.')


if __name__ == '__main__':
    r = Expr("""(a + a + b) * (a + b + b) * (b + b + c) *
                (b + c + c) * (c + c + a) * (c + a + a)""")
    n, e = r.crop(1)
    print('cropped', n, e)
    print('stitched', n.stitch(e))
    print(r)
    print(repr(r))
    v = {
        'a': ['1', '2'],
        'b': ['10', '20'],
        'c': ['100', '200'],
    }
    print(v)
    prec = gmpy2.ieee(32).precision - 1
    print(r.error(v, prec))
    for l, e in r.as_labels()[1].items():
        print(str(l), ':', str(e))
    print(r.area(v, prec))
    print(r.real_area(v, prec))
