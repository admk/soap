from soap.datatype import auto_type, type_of
from soap.datatype import cast as type_cast
from soap.expression.variable import Variable
from soap.lattice.map import MapLattice
from soap.semantics.error import cast, ErrorSemantics
from soap.semantics.linalg import MultiDimensionalArray
from soap.semantics.state.base import BaseState


class BoxState(BaseState, MapLattice):
    __slots__ = ()

    def _init_key_value(self, key, value):
        value = self._cast_value(key, value)
        if isinstance(key, str):
            key = Variable(key, type_of(value))
        elif isinstance(key, Variable):
            dtype = key.dtype
            if dtype is not auto_type and dtype != type_of(value):
                raise TypeError(
                    'Variable type is not the same as the type of value '
                    'to be assigned')
        return key, value

    def _cast_key(self, key, value=None):
        if isinstance(key, Variable):
            return key
        if isinstance(key, str):
            var_list = [var for var in self.keys() if var.name == key]
            if not var_list:
                raise KeyError(key)
            if len(var_list) > 1:
                raise KeyError('Multiple variables with the same name.')
            var = var_list.pop()
            return var
        raise TypeError(
            'Do not know how to convert {!r} into a variable'.format(key))

    def _cast_value(self, key=None, value=None, top=False, bottom=False):
        if top or bottom:
            return type_cast(key.dtype, value=value, top=top, bottom=bottom)
        if isinstance(value, MultiDimensionalArray):
            return value
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
                if not v.is_top() and not u.is_top():
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
