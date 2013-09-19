"""
.. module:: soap.semantics.state
    :synopsis: Program states.
"""
from soap import logger

from soap.lattice import denotational, map


class State(object):
    """Program state.

    This provides the base class of all denotational semantics-based state
    objects.
    """
    def __init__(self, *args, **kwargs):

        def decorate_assign(func):
            def assign(var, expr):
                state = func(var, expr)
                logger.debug(
                    '⟦' + str(var) + ' := ' + str(expr) + '⟧:',
                    str(self), '→', str(state))
                return state
            return assign

        def decorate_conditional(func):
            def conditional(expr, cond):
                state = func(expr, cond)
                logger.debug(
                    '⟦' + str(expr if cond else ~expr) + '⟧:',
                    str(self), '→', str(state))
                return state
            return conditional

        def decorate_join(func):
            def join(other):
                state = func(other)
                logger.debug(str(self) + ' ⊔ ' + str(other), '→', str(state))
                return state
            return join

        def decorate_le(func):
            def le(other):
                b = func(other)
                logger.debug(str(self), '⊑' if b else '⋢', str(other))
                return b
            return le

        super().__init__(*args, **kwargs)
        self.assign = decorate_assign(self.assign)
        self.conditional = decorate_conditional(self.conditional)
        self.join = decorate_join(self.join)
        self.le = decorate_le(self.le)

    def assign(self, var, expr):
        """Makes an assignment and returns a new state object."""
        mapping = dict(self.mapping)
        try:
            mapping[var] = expr.eval(self.mapping)
        except NameError:
            pass
        return self.__class__(mapping)

    def conditional(self, expr, cond):
        """Imposes a conditional on the state, returns a new state."""
        raise NotImplementedError


def denotational_state(cls=None, name=None):
    class DenotationalState(State, map(str, denotational(cls))):
        pass
    if name:
        DenotationalState.__name__ = name
    elif cls:
        DenotationalState.__name__ += cls.__name__
    return DenotationalState


class ClassicalState(denotational_state()):
    """The classical definition of a program state.

    This is intended to layout the foundation of future state classes,
    as well as to verify correctness of the program flows defined in
    :module:`soap.program.flow`.
    """
    def conditional(self, expr, cond):
        if expr.eval(self.mapping) == cond:
            return self
        return self.__class__(bottom=True)
