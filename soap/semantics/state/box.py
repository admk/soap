from soap.expression.variable import Variable
from soap.label.identifier import Identifier
from soap.lattice.map import map
from soap.semantics.error import cast, IntegerInterval, ErrorSemantics
from soap.semantics.state.base import BaseState
from soap.semantics.state.identifier import IdentifierBaseState
from soap.semantics.state.functions import bool_eval


class BoxState(BaseState, map(None, (IntegerInterval, ErrorSemantics))):
    __slots__ = ()

    def _cast_key(self, key):
        if isinstance(key, str):
            return Variable(key)
        if isinstance(key, Variable):
            return key
        raise TypeError(
            'Do not know how to convert {!r} into a variable'.format(key))

    def _cast_value(self, value=None, top=False, bottom=False):
        if top or bottom:
            return IntegerInterval(top=top, bottom=bottom)
        return cast(value)

    def is_fixpoint(self, other):
        """Checks if `self` is equal to `other` in the value ranges.

        For potential non-terminating loops, states are not the bottom element
        in the evaluation of loop statements even if a fixpoint is reached.
        This computation would result in a fixpoint of value ranges but
        the resulting error terms are strictly greater. Consequently for
        non-terminating loops the fixpoint for the error terms are always
        [-inf, inf] = ⊤. To gain any useful information about the program we
        wish to disregard the error terms and warn about non-termination.
        """
        if self.is_top() and other.is_top():
            return True
        if self.is_bottom() and other.is_bottom():
            return True
        non_bottom_keys = lambda d: set(
            [k for k, v in d.items() if not v.is_bottom()])
        if non_bottom_keys(self) != non_bottom_keys(other):
            return False
        for k, v in self.items():
            u = other[k]
            if type(v) is not type(u):
                return False
            if isinstance(v, ErrorSemantics):
                u, v = u.v, v.v
            if u != v:
                return False
        return True

    def widen(self, other):
        """Simple widening operator, jumps to infinity if interval widens.

        self.widen(other) => self ∇ other
        """
        if self.is_top() or other.is_bottom():
            return self
        if self.is_bottom() or other.is_top():
            return other
        mapping = dict(self)
        for k, v in other.items():
            if k not in mapping:
                mapping[k] = v
            else:
                mapping[k] = mapping[k].widen(v)
        return self.__class__(mapping)


class IdentifierBoxState(IdentifierBaseState, BoxState):
    __slots__ = ()

    def _cast_value(self, value=None, top=False, bottom=False):
        if not isinstance(value, Identifier):
            return super()._cast_value(value, top=top, bottom=bottom)
        return value

    def annotated_assignment(self, key, value, annotation):
        state = self.copy()
        state[Identifier(key, annotation=annotation)] |= value
        state[key] = value
        return state

    def bool_eval(self, expr):
        def conditional(cond):
            var, cstr = bool_eval(self, expr, cond)
            annotation = flow.annotation.attributed(cond)
            return self.annotated_assignment(var, cstr, annotation)
        return [conditional(True), conditional(False)]

    def visit_AssignFlow(self, flow):
        value = self._cast_value(self.arith_eval(flow.expr))
        return self.annotated_assignment(flow.var, value, flow.annotation)
