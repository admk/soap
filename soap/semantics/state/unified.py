from soap.expression import Expression, expression_factory, operators, Variable
from soap.lattice.meta import ComponentWiseLattice
from soap.semantics.state.arithmetic import IdentifierArithmeticState
from soap.semantics.state.base import BaseState
from soap.semantics.state.boolean import IdentifierBooleanState
from soap.semantics.state.box import IdentifierBoxState


class ConditionalResolutionError(ValueError):
    """Cannot resolve conditional. """


class SoapState(BaseState, ComponentWiseLattice):
    """Collects three classes of states into a unified state. """
    __slots__ = ()
    _component_classes = (
        IdentifierBoxState,
        IdentifierArithmeticState,
        IdentifierBooleanState,
    )

    def __init__(self, numerical=None, arithmetic=None, boolean=None,
                 top=False, bottom=False):
        super().__init__(
            numerical, arithmetic, boolean, top=top, bottom=bottom)

    @property
    def numerical(self):
        return self.components[0]

    @property
    def arithmetic(self):
        return self.components[1]

    @property
    def boolean(self):
        return self.components[2]

    def resolve_conditionals(self, expr):
        """Resolves boolean conditions in analysed expressions. """
        if isinstance(expr, Variable):
            return expr
        if isinstance(expr, Expression):
            if expr.op == operators.TERNARY_SELECT_OP:
                test, arg1, arg2 = expr.args
                if test in self.boolean:
                    resolved = arg1
                elif not test in self.boolean:
                    resolved = arg2
                else:
                    raise ConditionalResolutionError(
                        'Cannot resolve conditional, conditional {} does not'
                        'exist in analyzed conditionals'.format(test))
                return self.resolve_conditionals(resolved)
            args = (self.resolve_conditionals(a) for a in expr.args)
            return expression_factory(expr.op, *args)
        raise TypeError(
            'Do not know how to resolve conditionals for {}'.format(expr))

    def insert_conditionals(self, expr):
        """Inserts boolean conditions. """
        for b in self.boolean:
            # FIXME we currently does not allow any compounds in boolean
            # expressions, this includes negation.
            if b.op == operators.UNARY_NEGATION_OP:
                ...

    def assign(self, var, expr, annotation):
        """Makes an assignment and returns a new state object."""
        components = (c.assign(var, expr, annotation) for c in self.components)
        return self.__class__(*components)

    def conditional(self, expr, cond, annotation):
        """Imposes a conditional on the state, returns a new state."""
        components = (
            c.conditional(expr, cond, annotation) for c in self.components)
        return self.__class__(*components)

    def is_fixpoint(self, other):
        """Fixpoint test, defaults to equality."""
        return all(
            self_comp.is_fixpoint(other_comp)
            for self_comp, other_comp in zip(self.components, other.components)
        )

    def widen(self, other):
        """Widening, defaults to least upper bound (i.e. join)."""
        components = (
            self_comp.widen(other_comp)
            for self_comp, other_comp in zip(self.components, other.components)
        )
        return self.__class__(*components)
