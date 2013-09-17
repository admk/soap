"""
.. module:: soap.semantics.state
    :synopsis: Program states.
"""
from soap import logger
from soap.lattice import Lattice, flat, map


class State(Lattice):
    """Program state.

    This provides the base class of all denotational semantics-based state
    objects.
    """
    def assign(self, var, expr):
        """Makes an assignment and returns a new state object."""
        raise NotImplementedError

    def conditional(self, expr, cond):
        """Imposes a conditional on the state, returns a new state."""
        raise NotImplementedError


class ClassicalState(State):
    """The classical definition of a program state.

    This is intended to layout the foundation of future state classes,
    as well as to verify correctness of the program flows defined in
    :module:`soap.program.flow`.
    """

    top_magic = {'_': 'top'}
    bottom_magic = {}

    def __init__(self, mapping=None, top=False, bottom=False, **kwargs):
        if top:
            self.mapping = self.top_magic
        elif bottom:
            self.mapping = self.bottom_magic
        else:
            self.mapping = dict(mapping or {}, **kwargs)

    def top(self):
        return self.mapping == self.top_magic

    def bottom(self):
        return self.mapping == self.bottom_magic

    def assign(self, var, expr):
        mapping = dict(self.mapping)
        try:
            mapping[var] = expr.eval(self.mapping)
        except NameError:
            pass
        state = ClassicalState(mapping)
        logger.debug(
            '⟦' + str(var) + ' := ' + str(expr) + '⟧:',
            str(self), '→', str(state))
        return state

    def conditional(self, expr, cond):
        if expr.eval(self.mapping) == cond:
            state = self
        else:
            state = ClassicalState(bottom=True)
        logger.debug(
            '⟦' + str(expr if cond else ~expr) + '⟧:',
            str(self), '→', str(state))
        return state

    def join(self, other):
        if other.top():
            return other
        if other.bottom():
            return self
        mapping = dict(self.mapping)
        for k, v in other.mapping.items():
            if k in mapping and mapping[k] != v:
                return ClassicalState(top=True)
            mapping[k] = v
        state = ClassicalState(mapping)
        logger.debug(str(self) + ' ⊔ ' + str(other), '→', str(state))
        return state

    def __le__(self, other):
        if other.top():
            b = True
        elif other.bottom():
            b = False
        elif set(self.mapping.items()) <= set(other.mapping.items()):
            b = True
        else:
            b = False
        logger.debug(str(self), '⊑' if b else '⋢', str(other))
        return b

    def __str__(self):
        if self.mapping:
            s = '[%s]' % ', '.join(
                str(k) + '↦' + str(v) for k, v in self.mapping.items())
        elif self.top():
            s = '⊤'
        elif self.bottom():
            s = '⊥'
        return s
