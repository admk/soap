"""
.. module:: soap.semantics.common
    :synopsis: Common definitions for semantics.
"""
import gmpy2


_label_count = 0
_labels = None


def fresh_int(e):
    """Generates a fresh int for the label of the expression `e`."""
    global _label_count, _labels
    _labels = _labels or {}
    if e in _labels:
        return _labels[e]
    _label_count += 1
    _labels[e] = _label_count
    return _label_count


class Label(object):
    """Constructs a label for the expression `e`"""
    def __init__(self, e, l=None):
        self.l = l or fresh_int(e)
        self.e = e
        self.__slots__ = []
        super().__init__()

    def signal_name(self):
        return 's_%d' % self.l

    def port_name(self):
        from soap.expr.common import OPERATORS
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
    """Not used... Check if this can be removed."""
    def __init__(self, s):
        self.s = {fresh_int: e for e in s}
        super().__init__()

    def add(self, e):
        if e in list(self.s.items()):
            return
        self.s[Label()] = e


def precision_context(prec):
    """Withable context for changing precisions. Unifies how precisions can be
    changed.

    :param prec: The mantissa width.
    :type prec: int
    """
    # prec is the mantissa width
    # need to include the implicit integer bit for gmpy2
    prec += 1
    return gmpy2.local_context(gmpy2.ieee(128), precision=prec)
