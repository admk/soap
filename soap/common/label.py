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
    """Constructs a label for expression or statement `statement`"""
    __slots__ = ('label_value', 'statement', 'description')

    def __init__(self, statement=None, label_value=None, description=None):
        self.label_value = label_value or fresh_int(
            (statement, self.__class__))
        self.statement = statement
        self.description = description
        super().__init__()

    def signal_name(self):
        return 's_{}'.format(self.label_value)

    def port_name(self):
        from soap.expression.operators import OPERATORS
        forbidden = OPERATORS + [',', '(', ')', '[', ']']
        if any(k in str(self.e) for k in forbidden):
            s = self.label_value
        else:
            s = self.statement
        return 'p_%s' % str(s)

    def __str__(self):
        s = 'l{}'.format(self.label_value)
        if self.description:
            s += ':{.desc}'.format(self)
        return s

    def __repr__(self):
        return '{cls}({statement!r}, {label!r})'.format(
            cls=self.__class__.__name__,
            statement=self.statement,
            label=self.label_value)

    def __eq__(self, other):
        if not isinstance(other, Label):
            return False
        return self.label_value == other.label_value

    def __hash__(self):
        return hash(self.label_value)


class FlowLabel(Label):
    def __init__(self, flow=None, iteration=0):
        super().__init__(label_value=fresh_int(flow))
        self.statement = flow
        self.iteration = iteration

    def __eq__(self, other):
        if not isinstance(other, FlowLabel):
            return False
        if self.label_value != other.label_value:
            return False
        return self.iteration == other.iteration

    def __hash__(self):
        return hash((self.label_value, self.iteration))


class Labels(object):
    """Not used... Check if this can be removed."""
    def __init__(self, s):
        self.s = {fresh_int: e for e in s}
        super().__init__()

    def add(self, e):
        if e in list(self.s.items()):
            return
        self.s[Label()] = e


def superscript(label):
    return label
