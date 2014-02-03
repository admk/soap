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

    def pre_conditional(self, expr, cond, annotation):
        """Imposes a conditional on the state, returns a new state."""
        return self, self

    def post_conditional(self, expr, true_state, false_state, annotation):
        mapping = {}
        for k, v in set(true_state.items()) | set(false_state.items()):
            # if is not final identifier, keep its value
            if not k.annotation.is_bottom():
                existing_value = mapping.get(k)
                if existing_value and existing_value != v:
                    raise ValueError(
                        'Conflict in mapping update, same key {k}, '
                        'but different values {v}, {existing_value}'.format(
                            k=k, v=v, existing_value=existing_value))
                mapping[k] = v
                continue
            # if is final identifier, check final value conflicts;
            true_value, false_value = true_state[k], false_state[k]
            if true_value == false_value:
                mapping[k] = true_value
                continue
            # if has branch conflict, insert conditional
            join_id = Identifier(k.variable, annotation=annotation)
            mapping[k] = join_id
            mapping[join_id] = expression_factory(
                TERNARY_SELECT_OP, self._cast_value(expr),
                true_value, false_value)
        return self.__class__(mapping)

    def widen(self, other):
        """No widening is possible, simply return other.

        TODO widening should be elimination of deep recursions.
        """
        return other
