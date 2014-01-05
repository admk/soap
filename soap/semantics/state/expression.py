from soap.expression import Expression, expression_factory, Variable
from soap.label import Annotation, Identifier
from soap.lattice import Lattice, map
from soap.semantics.common import is_numeral
from soap.semantics.state.identifier import IdentifierBaseState


class IdentifierExpressionState(IdentifierBaseState, map()):
    """Analyzes variable identifiers to be represented with expressions. """
    __slots__ = ()

    def eval(self, expr, var=None):
        if isinstance(expr, Lattice):
            if expr.is_top() or expr.is_bottom():
                return expr
        if is_numeral(expr):
            return expr
        if isinstance(expr, Expression):
            return expression_factory(
                expr.op, *[self.eval(a) for a in expr.args])
        if isinstance(expr, Variable):
            value = self.get(
                Identifier(expr, annotation=Annotation(bottom=True)), None)
            if value is not None:
                return value
            # initial variable
            return Identifier(expr, annotation=Annotation(top=True))
        if isinstance(expr, Identifier):
            if not var or expr.variable != var:
                return expr
            # bump iteration for variable
            return Identifier(expr.variable, expr.label, expr.iteration + 1)

    def _cast_value(self, v=None, top=False, bottom=False):
        if top or bottom:
            return Expression(top=top, bottom=bottom)
        return self.eval(v)

    def _key_value_for_top_iteration(self, key, value):
        return key, self.eval(value, key.variable)

    def _key_value_for_consecutive_iteration(self, key, value):
        return key.prev_iteration(), self.eval(self[key], key.variable)

    def _key_value_for_bottom_iteration(self, key, value):
        return key.global_final(), key

    def assign(self, var, expr, annotation):
        """Makes an assignment and returns a new state object."""
        identifier = Identifier(var, annotation=annotation)
        return self[identifier:self.eval(expr, var)]

    def conditional(self, expr, cond, annotation):
        """Imposes a conditional on the state, returns a new state."""
        raise NotImplementedError

    def widen(self, other):
        """No widening is possible, simply return other.

        TODO widening should be elimination of deep recursions.
        """
        return other
