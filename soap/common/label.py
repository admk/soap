from soap.common.cache import Flyweight


_label_count = 0
_label_map = None


def fresh_int(e=None):
    """Generates a fresh int for the label of the expression `e`."""
    def _incr():
        global _label_count
        _label_count += 1
        return _label_count
    global _label_map
    _label_map = _label_map or {}
    if e is not None and e in _label_map:
        return _label_map[e]
    l = _incr()
    if e is not None:
        _label_map[e] = l
    return l


class Label(Flyweight):
    """Constructs a label for the expression `e`"""
    __slots__ = ('l', 'e', 'desc')

    def __init__(self, e=None, l=None, desc=None):
        self.l = l or fresh_int(e)
        self.e = e
        self.desc = desc
        super().__init__()

    def signal_name(self):
        return 's_%d' % self.l

    def port_name(self):
        from soap.expression.common import OPERATORS
        forbidden = OPERATORS + [',', '(', ')', '[', ']']
        if any(k in str(self.e) for k in forbidden):
            s = self.l
        else:
            s = self.e
        return 'p_%s' % str(s)

    def __str__(self):
        s = 'l{}'.format(self.l)
        if self.desc:
            s += ':{.desc}'.format(self)
        return s

    def __repr__(self):
        return 'Label({!r}, {!r})'.format(self.e, self.l)

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
