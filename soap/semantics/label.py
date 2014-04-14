from soap.common import Flyweight, Comparable
from soap.expression.common import is_expression


class LabelSemantics(Flyweight, Comparable):
    """The semantics that captures the area of an expression."""
    def __init__(self, label, env):
        """The labelling semantics.  """
        super().__init__()
        self.label = label
        self.env = env

    @property
    def luts(self, state, prec):
        try:
            return self._area
        except AttributeError:
            pass
        area = 0
        for v in self.env.values():
            if is_expression(v):
                area += v.operator_area(state, prec)
        self._area = area
        return area

    def __iter__(self):
        return iter((self.label, self.env))

    def __lt__(self, other):
        if not isinstance(other, LabelSemantics):
            return False
        return self.area < other.area

    def __eq__(self, other):
        if not isinstance(other, LabelSemantics):
            return False
        if self.area != other.area:
            return False
        return True

    def __str__(self):
        env = ', '.join('{} ↦ {}'.format(k, v) for k, v in self.env.items())
        env = '[{}]'.format(env)
        return '({label}, {env})'.format(label=self.label, env=env)

    def __repr__(self):
        return '{cls}({label!r}, {env!r})'.format(
            cls=self.__class__.__name__, label=self.label, env=self.env)
