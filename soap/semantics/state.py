"""
.. module:: soap.semantics.state
    :synopsis: Program states.
"""
import copy

from soap.semantics.common import Lattice


class State(Lattice):
    """Program state."""
    def copy(self):
        """Makes a copy of itself."""
        return copy.deepcopy(self)

    def assign(self, var, expr):
        """Makes an assignment and returns a new state object."""
        raise NotImplementedError

    def conditional(self, expr, cond):
        """Imposes a conditional on the state, returns a new state."""
        raise NotImplementedError


class ClassicalState(State):
    """The classical definition of a program state."""
    def __init__(self, mapping=None, **kwargs):
        self.mapping = dict(mapping or {}, **kwargs)

    def assign(self, var, expr):
        copy = self.copy()
        copy.mapping[var] = expr.eval(copy.mapping)
        return copy

    def conditional(self, expr, cond):
        if expr.eval(self.mapping) == cond:
            return self
        return self.__class__.bottom()

    def join(self, other):
        if other == self.__class__.bottom():
            return self
        if other == self.__class__.top():
            return other
        copy = self.copy()
        for k, v in other.mapping.items():
            if k in copy.mapping and copy.mapping[k] != v:
                return self.__class__.top()
            copy[k] = v
        return copy

    def __le__(self, other):
        if other == self.__class__.bottom():
            return False
        if other == self.__class__.top():
            return True
        if set(self.mapping.items()) <= set(other.mapping.items()):
            return True
        return False

    def __str__(self):
        return str(self.mapping)
