from soap.lattice.meta import ComponentWiseLattice
from soap.semantics.state.arithmetic import IdentifierArithmeticState
from soap.semantics.state.base import BaseState
from soap.semantics.state.box import IdentifierBoxState


class ConditionalResolutionError(ValueError):
    """Cannot resolve conditional. """


class SoapState(BaseState, ComponentWiseLattice):
    """Collects three classes of states into a unified state. """
    __slots__ = ()
    _component_classes = (
        IdentifierBoxState,
        IdentifierArithmeticState,
    )

    def __init__(
            self, numerical=None, arithmetic=None, top=False, bottom=False):
        super().__init__(numerical, arithmetic, top=top, bottom=bottom)

    @property
    def numerical(self):
        return self.components[0]

    @property
    def arithmetic(self):
        return self.components[1]

    def assign(self, var, expr, annotation):
        """Makes an assignment and returns a new state object."""
        components = (c.assign(var, expr, annotation) for c in self.components)
        return self.__class__(*components)

    def conditional(self, expr, cond, annotation):
        """Imposes a conditional on the state, returns a new state."""
        components = (
            c.conditional(expr, cond, annotation) for c in self.components)
        return self.__class__(*components)

    def is_fixpoint(self, other):
        """Fixpoint test, defaults to equality."""
        return all(
            self_comp.is_fixpoint(other_comp)
            for self_comp, other_comp in zip(self.components, other.components)
        )

    def widen(self, other):
        """Widening, defaults to least upper bound (i.e. join)."""
        components = (
            self_comp.widen(other_comp)
            for self_comp, other_comp in zip(self.components, other.components)
        )
        return self.__class__(*components)
