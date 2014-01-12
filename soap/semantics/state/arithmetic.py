from soap.expression import (
    ArithExpr, Expression, expression_factory, Variable, parse
)
from soap.label import Annotation, Identifier
from soap.lattice import Lattice, map
from soap.semantics.common import is_numeral
from soap.semantics.state.identifier import IdentifierBaseState


class IdentifierArithmeticState(
        IdentifierBaseState, map(Identifier, ArithExpr)):
    """Analyzes variable identifiers to be represented with expressions. """
    __slots__ = ()

    def _cast_value(self, expr=None, top=False, bottom=False):
        if top or bottom:
            return ArithExpr(top=top, bottom=bottom)
        if isinstance(expr, Lattice):
            if expr.is_top() or expr.is_bottom():
                return expr
        if is_numeral(expr):
            return expr
        if isinstance(expr, Expression):
            return expression_factory(
                expr.op, *[self._cast_value(a) for a in expr.args])
        if isinstance(expr, Variable):
            return self.get(
                Identifier(expr, annotation=Annotation(bottom=True)),
                Identifier(expr, annotation=Annotation(top=True)))
        if isinstance(expr, Identifier):
            return expr
        if isinstance(expr, str):
            return self._cast_value(parse(expr))
        raise TypeError('Do not know how to evaluate {!r}'.format(expr))

    def assign(self, var, expr, annotation):
        """Makes an assignment and returns a new state object."""
        return self.increment(Identifier(var, annotation=annotation), expr)

    def conditional(self, expr, cond, annotation):
        """Imposes a conditional on the state, returns a new state."""
        return self

    def widen(self, other):
        """No widening is possible, simply return other.

        TODO widening should be elimination of deep recursions.
        """
        return other
