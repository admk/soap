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

    def pre_conditional(self, expr, annotation):
        """Imposes a conditional on the state, returns a new state.  """
        def assign_conditional(state, variable):
            """Constructs conditional expression assignment for the conditional
            annotation.  For example, if (x < 1)l0 (x = x + 1)l1 gives
            x^l0_conditional := x0 < 1.  This helps with iteration increment of
            the conditional expression.  """
            return state.assign(
                variable, expr, annotation.attributed_conditional())

        def assign_split_values(state, variable, annotations):
            """Adds true and false versions of the variable under true and
            false labels.  """
            for annotation in annotations:
                state = state.assign(variable, self[variable], annotation)
            return state

        def iterate_split_finals(state, variable):
            """Iterates split states, with true and false being final values in
            sequence.  """
            false_annotations = [
                annotation.attributed_true(),
                annotation.attributed_false(),
            ]
            true_annotations = reversed(false_annotations)
            for annotations in [true_annotations, false_annotations]:
                yield assign_split_values(state, variable, annotations)

        variable = expr.a1
        state = assign_conditional(self, variable)
        return tuple(iterate_split_finals(state, variable))

    def _post_conditional_join_value(
            self, final_key, true_value, false_value, annotation):
        # check final values in branched states for conflicts
        if true_value == false_value:
            # no conflict, return same value
            return true_value
        # if has branch conflict, insert conditional
        conditional_identifier = Identifier(
            variable=final_key.variable,
            annotation=annotation.attributed_conditional())
        return expression_factory(
            TERNARY_SELECT_OP, conditional_identifier,
            true_value, false_value)

    def widen(self, other):
        """No widening is possible, simply return other."""
        return other
