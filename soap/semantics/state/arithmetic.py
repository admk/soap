from soap.expression import (
    ArithExpr, Expression, expression_factory, Variable, parse
)
from soap.expression.operators import TERNARY_SELECT_OP
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
        if isinstance(expr, Expression):
            return expression_factory(
                expr.op, *[self._cast_value(a) for a in expr.args])
        if isinstance(expr, Lattice):
            if expr.is_top() or expr.is_bottom():
                return expr
        if isinstance(expr, Variable):
            return self.get(
                Identifier(expr, annotation=Annotation(bottom=True)),
                Identifier(expr, annotation=Annotation(top=True)))
        if is_numeral(expr):
            return expr
        if isinstance(expr, Identifier):
            return expr
        if isinstance(expr, str):
            parsed_expr = parse(expr)
            if not isinstance(parsed_expr, ArithExpr):
                raise ValueError(
                    'Expression {expr!r} is not an arithmetic expression.'
                    .format(expr=expr))
            return self._cast_value(parsed_expr)
        raise TypeError('Do not know how to evaluate {!r}'.format(expr))

    def assign(self, var, expr, annotation):
        """Makes an assignment and returns a new state object."""
        return self.increment(Identifier(var, annotation=annotation), expr)

    def pre_conditional(self, expr, true_annotation, false_annotation):
        """Imposes a conditional on the state, returns a new state.

        TODO decide whether conditional should be assigned or not.
        For example, the program `if (x < 1)l0 (x = x - 1)l1 (x = x + 1)l2` for
        an empty input should produce as the output::

            x := x0 < 1 ? x0 - 1 : x0 + 1

        or::

            x := x0 < 1 ? xl0t - 1 : xl0f + 1, xl0t := x0, xl0f := x0

        Currently it is the first one.
        """
        return self, self

    def _post_conditional_join_value(
            self, conditional_expr, final_key, true_state, false_state):
        true_final_value = true_state[final_key]
        false_final_value = false_state[final_key]
        # check final values in branched states for conflicts
        if true_final_value == false_final_value:
            # no conflict, return same value
            return true_final_value
        # if has branch conflict, insert conditional
        return expression_factory(
            TERNARY_SELECT_OP, self._cast_value(conditional_expr),
            true_final_value, false_final_value)

    def widen(self, other):
        """No widening is possible, simply return other."""
        return other
