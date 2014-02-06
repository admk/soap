from soap.semantics.state.arithmetic import IdentifierArithmeticState
from soap.semantics.state.base import BaseState
from soap.semantics.state.box import IdentifierBoxState


class ConditionalResolutionError(ValueError):
    """Cannot resolve conditional. """


class SoapState(BaseState, IdentifierBoxState * IdentifierArithmeticState):
    """Collects three classes of states into a unified state. """
    __slots__ = ()

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
        components = tuple(
            c.assign(var, expr, annotation) for c in self.components)
        return self.__class__(*components)

    def pre_conditional(self, expr, true_annotation, false_annotation):
        """Imposes a conditional on the state, returns a new state."""
        zipped_components = tuple(
            c.pre_conditional(expr, true_annotation, false_annotation)
            for c in self.components)
        return (self.__class__(*components)
                for components in zip(*zipped_components))

    def post_conditional(self, expr, true_state, false_state, annotation):
        """Imposes a conditional on the state, returns a new state."""
        zipper_components = zip(
            self.components, true_state.components, false_state.components)
        components = tuple(
            c.post_conditional(expr, t, f, annotation)
            for c, t, f in zipper_components)
        return self.__class__(*components)

    def is_fixpoint(self, other):
        """Fixpoint test, defaults to equality."""
        return all(
            self_comp.is_fixpoint(other_comp)
            for self_comp, other_comp in zip(self.components, other.components)
        )

    def widen(self, other):
        """Widening, defaults to least upper bound (i.e. join)."""
        components = tuple(
            self_comp.widen(other_comp)
            for self_comp, other_comp in zip(self.components, other.components)
        )
        return self.__class__(*components)
