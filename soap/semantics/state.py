"""
.. module:: soap.semantics.state
    :synopsis: Program states.
"""
from soap import logger
from soap.semantics import mpfr
from soap.lattice import value, map


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
            def __le__(other):
                b = func(other)
                logger.debug(str(self), '⊑' if b else '⋢', str(other))
                return b
            return __le__

        super().__init__(*args, **kwargs)
        self.assign = decorate_assign(self.assign)
        self.conditional = decorate_conditional(self.conditional)
        self.join = decorate_join(self.join)
        self.__le__ = decorate_le(self.__le__)

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

    def __str__(self):
        if self.mapping:
            s = '[%s]' % ', '.join(
                str(k) + '↦' + str(v) for k, v in self.mapping.items())
        elif self.is_top():
            s = '⊤'
        elif self.is_bottom():
            s = '⊥'
        return s
    __repr__ = __str__


def value_state(cls, name=None):
    class S(State, map(str, value(cls))):
        pass
    if name:
        S.__name__ = name
    else:
        S.__name__ = 'State_' + cls.__name__
    return S


class ClassicalState(value_state(mpfr)):
    """The classical definition of a program state.

    This is intended to layout the foundation of future state classes,
    as well as to verify correctness of the program flows defined in
    :module:`soap.program.flow`.
    """
    def conditional(self, expr, cond):
        if expr.eval(self.mapping) == cond:
            return self
        return self.__class__(bottom=True)
