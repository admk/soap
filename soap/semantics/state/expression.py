from soap.context import context
from soap.expression import Expression, expression_factory, Variable
from soap.label import Annotation, Identifier, Iteration
from soap.lattice.map import map
from soap.semantics.state.identifier import IdentifierBaseState


class IdentifierExpressionState(
        IdentifierBaseState, map(Identifier, Expression)):
    """Analyzes variable identifiers to be represented with expressions. """
    def _cast_value(self, v=None, top=False, bottom=False):
        ...

    def _key_value_for_top_iteration(self, key, value):
        ...

    def _key_value_for_consecutive_iteration(self, key, value):
        ...

    def assign(self, var, expr, annotation):
        """Makes an assignment and returns a new state object."""
        def eval(self, var, expr):
            """
            Evaluates a syntactic expression into an expression of identifiers.
            """
            if isinstance(expr, Variable):
                # expr is a variable, try to find the current expression value
                # of the variable
                return self[Identifier(expr, annotation=Annotation(top=True))]
            if isinstance(expr, Identifier):
                if expr.variable != var:
                    return expr
                if expr.iteration.is_bottom():
                    iteration = Iteration(0)
                else:
                    iteration = expr.iteration
                iteration += 1
                if iteration > context.program_depth:
                    iteration = Iteration(top=True)
                return Identifier(expr.variable, expr.label, iteration)
            if isinstance(expr, Expression):
                return expression_factory(
                    expr.op, (self.eval(a) for a in expr.args))
            return
        mapping = dict(self)
        mapping[Identifier(var, annotation=annotation)] = self.eval(expr)
        return self.__class__(mapping)

    def conditional(self, expr, cond, annotation):
        """Imposes a conditional on the state, returns a new state."""
        raise NotImplementedError

    def widen(self, other):
        """No widening is possible, simply return other.

        TODO widening should be elimination of deep recursions.
        """
        return other
