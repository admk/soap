from soap.expression import Expression, expression_factory, Variable
from soap.label import Annotation, Identifier
from soap.lattice import Lattice, map
from soap.semantics.common import is_numeral
from soap.semantics.state.identifier import IdentifierBaseState


class IdentifierExpressionState(IdentifierBaseState, map()):
    """Analyzes variable identifiers to be represented with expressions. """
    __slots__ = ()

    def _cast_value(self, expr=None, top=False, bottom=False):
        if top or bottom:
            return Expression(top=top, bottom=bottom)
        if isinstance(expr, Lattice):
            if expr.is_top() or expr.is_bottom():
                return expr
        if is_numeral(expr):
            return expr
        if isinstance(expr, Expression):
            return expression_factory(
                expr.op, *[self._cast_value(a) for a in expr.args])
        if isinstance(expr, Variable):
            value = self.get(
                Identifier(expr, annotation=Annotation(bottom=True)), None)
            if value is not None:
                return value
            # initial variable
            return Identifier(expr, annotation=Annotation(top=True))
        if isinstance(expr, Identifier):
            return expr
        raise TypeError('Do not know how to evaluate {!r}'.format(expr))

    def _increment(self, value, identifier):
        if isinstance(value, Lattice):
            if value.is_top() or value.is_bottom():
                return value
        if isinstance(value, Expression):
            args = [self._increment(a, identifier) for a in value.args]
            return expression_factory(value.op, *args)
        if isinstance(value, Identifier):
            if value.variable == identifier.variable:
                if value.label == identifier.label:
                    return value.prev_iteration()
            return value
        if is_numeral(value):
            return value
        raise TypeError('Do not know how to increment {!r}'.format(value))

    def assign(self, var, expr, annotation):
        """Makes an assignment and returns a new state object."""
        return self.increment(Identifier(var, annotation=annotation), expr)

    def conditional(self, expr, cond, annotation):
        """Imposes a conditional on the state, returns a new state."""
        raise NotImplementedError

    def widen(self, other):
        """No widening is possible, simply return other.

        TODO widening should be elimination of deep recursions.
        """
        return other
