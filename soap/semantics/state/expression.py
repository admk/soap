from soap.expression import Expression, expression_factory, Variable
from soap.label import Annotation, Identifier, Iteration
from soap.lattice.map import map
from soap.semantics.state.base import BaseState


class IdentifierExpressionState(BaseState, map(Identifier, Expression)):
    """Analyzes variable identifiers to be represented with expressions. """
    iteration_limit = 3

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # update the mapping with the current identifiers of variables
        for k, v in self.items():
            identifier = Identifier(
                k.variable, annotation=Annotation(top=True))
            self[identifier] = k

    def _cast_key(self, key):
        """Convert a variable into an identifier.

        An initial identifier of a variable is always::
            ([variable_name], ⊥, ⊥)
        """
        if isinstance(key, Identifier):
            return key
        if isinstance(key, str):
            key = Variable(key)
        if isinstance(key, Variable):
            return Identifier(key, annotation=Annotation(bottom=True))
        raise TypeError(
            'Do not know how to convert {!r} into an identifier'.format(key))

    def _cast_value(self, v=None, top=False, bottom=False):
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
                if iteration > self.iteration_limit:
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
