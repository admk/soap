import gmpy2


_label_count = 0
_labels = None


def fresh_int(e):
    global _label_count, _labels
    _labels = _labels or {}
    if e in _labels:
        return _labels[e]
    _label_count += 1
    _labels[e] = _label_count
    return _label_count


class Label(object):

    def __init__(self, e, l=None):
        self.l = l or fresh_int(e)
        self.e = e
        self.__slots__ = []
        super().__init__()

    def signal_name(self):
        return 's_%d' % self.l

    def port_name(self):
        from ce.expr.common import OPERATORS
        forbidden = OPERATORS + [',', '(', ')', '[', ']']
        if any(k in str(self.e) for k in forbidden):
            s = self.l
        else:
            s = self.e
        return 'p_%s' % str(s)

    def __str__(self):
        return 'l%s' % str(self.l)

    def __repr__(self):
        return 'Label(%s, %s)' % (repr(self.e), repr(self.l))

    def __eq__(self, other):
        if not isinstance(other, Label):
            return False
        return self.l == other.l

    def __lt__(self, other):
        if not isinstance(other, Label):
            return False
        return self.l < other.l

    def __hash__(self):
        return hash(self.l)


class Labels(object):

    def __init__(self, s):
        self.s = {fresh_int: e for e in s}
        super().__init__()

    def add(self, e):
        if e in list(self.s.items()):
            return
        self.s[Label()] = e


class Lattice(object):

    def join(self, other):
        raise NotImplementedError

    def meet(self, other):
        raise NotImplementedError

    def __or__(self, other):
        return self.join(other)

    def __and__(self, other):
        return self.meet(other)


def precision_context(prec):
    return gmpy2.local_context(gmpy2.ieee(128), precision=prec)
