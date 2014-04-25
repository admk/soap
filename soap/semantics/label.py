from collections import namedtuple

from soap.common import Flyweight, Comparable
from soap.expression.common import is_expression


_label_semantics_tuple_type = namedtuple('LabelSemantics', ['label', 'env'])


class LabelSemantics(_label_semantics_tuple_type, Flyweight, Comparable):
    """The semantics that captures the area of an expression."""

    def luts(self, exponent, mantissa):
        try:
            return self._area
        except AttributeError:
            pass

        def accumulate_luts_count(env):
            luts = 0
            for v in env.values():
                if is_expression(v):
                    luts += v.operator_luts(exponent, mantissa)
                if isinstance(v, dict):
                    luts += accumulate_luts_count(v)
            return luts

        self._luts = accumulate_luts_count(self.env)
        return self._luts

    def __iter__(self):
        return iter((self.label, self.env))

    def __lt__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.area < other.area

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.area != other.area:
            return False
        return True
