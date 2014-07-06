from collections import namedtuple

from soap.common import Comparable, Flyweight
from soap.expression import External, FixExpr, is_expression
from soap.flopoco.statistics import operator_luts


_label_semantics_tuple_type = namedtuple('LabelSemantics', ['label', 'env'])


class LabelSemantics(_label_semantics_tuple_type, Flyweight, Comparable):
    """The semantics that captures the area of an expression."""

    def __new__(cls, label, env):
        from soap.semantics.state import MetaState
        return super().__new__(cls, label, MetaState(env))

    def __init__(self, label, env):
        super().__init__()
        self._luts = None

    def luts(self, exponent, mantissa):
        if self._luts is not None:
            return self._luts

        def accumulate_luts_count(env):
            luts = 0
            for v in env.values():
                if is_expression(v) and not isinstance(v, External):
                    luts += operator_luts(v.op, exponent, mantissa)
                if isinstance(v, FixExpr):
                    luts += accumulate_luts_count(v.bool_expr[1])
                    luts += accumulate_luts_count(v.loop_state)
                    luts += accumulate_luts_count(v.init_state)
            return luts

        self._luts = accumulate_luts_count(self.env)
        return self._luts

    def __iter__(self):
        return iter((self.label, self.env))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.label == other.label and self.env == other.env

    def __hash__(self):
        return hash((self.__class__, self.label, self.env))

    def __str__(self):
        return '({}, {})'.format(self.label, self.env)
