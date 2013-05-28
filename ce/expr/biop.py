import gmpy2

from ce.common import Comparable, Flyweight, cached

from ce.expr.common import ADD_OP, MULTIPLY_OP, COMMUTATIVITY_OPERATORS
from ce.expr.parser import parse


class Var(Comparable, Flyweight):

    __slots__ = ()

    def __init__(self, v, prec):
        self.v = v
        self.prec = prec

    def context(self):
        return gmpy2.context(precision=self.prec)


class Expr(Comparable, Flyweight):

    __slots__ = ('op', 'a1', 'a2', 'prec', '_hash')

    def __init__(self, *args, **kwargs):
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
        def to_tuple(a):
            if isinstance(a, Expr):
                return a.tree()
            return a
        return (self.op, to_tuple(self.a1), to_tuple(self.a2))

    @property
    def args(self):
        return [self.a1, self.a2]

    @cached
    def error(self, v):
        def eval(a):
            from ce.semantics import cast_error, cast_error_constant
            try:
                return a.error(v)
            except AttributeError:
                pass
            try:
                return eval(v[a])
            except (TypeError, KeyError):
                pass
            try:
                return cast_error_constant(a)
            except TypeError:
                pass
            try:
                return cast_error(*a)
            except TypeError:
                return a
        e1, e2 = eval(self.a1), eval(self.a2)
        if self.op == ADD_OP:
            return e1 + e2
        if self.op == MULTIPLY_OP:
            return e1 * e2

    @cached
    def area(self, v):
        from ce.semantics import AreaSemantics
        return AreaSemantics(self, v)

    @cached
    def as_labels(self):
        from ce.semantics import Label

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
        from ce.semantics import Label
        l = Label(self)
        return l, {l: self}

    def stitch(self, env):
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
        return "Expr(op='%s', a1=%s, a2=%s)" % \
            (self.op, repr(self.a1), repr(self.a2))

    def __add__(self, other):
        return Expr(op=ADD_OP, a1=self, a2=other)

    def __mul__(self, other):
        return Expr(op=MULTIPLY_OP, a1=self, a2=other)

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

    __slots__ = Expr.__slots__

    def __init__(self, **kwargs):
        from ce.semantics import Label
        super().__init__(**kwargs)
        if not isinstance(self.a1, Label) or not isinstance(self.a2, Label):
            raise ValueError('BExpr allows only binary expressions.')


if __name__ == '__main__':
    gmpy2.set_context(gmpy2.ieee(32))
    r = Expr('(a + 1) * (a + b + [2, 3])')
    n, e = r.crop(1)
    print('cropped', n, e)
    print('stitched', n.stitch(e))
    print(r)
    print(repr(r))
    v = {
        'a': ['0.2', '0.3'],
        'b': ['2.3', '2.4']
    }
    print(v)
    print(r.error(v))
    for e, v in r.as_labels()[1].items():
        print(str(e), ':', str(v))
    print(r.area(v))
