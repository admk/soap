from soap.expression.boolean import BoolExpr
from soap.lattice.list import list
from soap.semantics.state.base import BaseState
from soap.semantics.state.identifier import IdentifierBaseState


class IdentifierBooleanState(BaseState, IdentifierBaseState, list(BoolExpr)):
    """Analyzes boolean constraints into a list of boolean selectors. """
    def increment_for_key(self, key):
        pass

    def assign(self, var, expr, annotation):
        """Makes an assignment and returns a new state object."""
        return self

    def conditional(self, expr, cond, annotation):
        """Imposes a conditional on the state, returns a new state."""
        return self.append(self.eval(expr))

    def widen(self, other):
        """No widening is possible, simply return other.

        TODO widening should be elimination of deep recursions.
        """
        return other
