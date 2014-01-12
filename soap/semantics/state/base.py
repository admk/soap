from functools import wraps

from soap import logger
from soap.label import superscript


def _decorate(cls):
    def decorate_assign(func):
        @wraps(func)
        def assign(self, var, expr, annotation):
            state = func(self, var, expr, annotation)
            logger.debug(
                '⟦[{var} := {expr}]{annotation}⟧{prev} → {next}'.format(
                    var=var, expr=expr, annotation=superscript(annotation),
                    prev=self, next=state))
            return state
        return assign

    def decorate_conditional(func):
        @wraps(func)
        def conditional(self, expr, cond, annotation):
            state = func(self, expr, cond, annotation)
            if cond:
                expr = ~expr
            logger.debug(
                '⟦[{expr}]{annotation}⟧{prev} → {next}'.format(
                    expr=expr, annotation=superscript(annotation),
                    prev=self, next=state))
            return state
        return conditional

    def decorate_join(func):
        @wraps(func)
        def join(self, other):
            state = func(self, other)
            logger.debug('{prev} ⊔ {other} → {next}'.format(
                prev=self, other=other, next=state))
            return state
        return join

    def decorate_le(func):
        @wraps(func)
        def le(self, other):
            b = func(self, other)
            logger.debug('{prev} {le_or_nle} {other}'.format(
                prev=self, le_or_nle='⊑⋢'[b], other=other))
            return b
        return le

    try:
        if cls == BaseState or cls._state_decorated:
            return
    except AttributeError:
        cls._state_decorated = True
    cls.assign = decorate_assign(cls.assign)
    cls.conditional = decorate_conditional(cls.conditional)
    cls.join = decorate_join(cls.join)
    cls.le = decorate_le(cls.le)


class BaseState(object):
    """Base state for all program states."""
    __slots__ = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _decorate(self.__class__)

    def _cast_key(self, key):
        raise NotImplementedError

    def _cast_value(self, v=None, top=False, bottom=False):
        raise NotImplementedError

    def assign(self, var, expr, annotation):
        """Makes an assignment and returns a new state object."""
        raise NotImplementedError

    def conditional(self, expr, cond, annotation):
        """Imposes a conditional on the state, returns a new state."""
        raise NotImplementedError

    def is_fixpoint(self, other):
        """Fixpoint test, defaults to equality."""
        return self == other

    def widen(self, other):
        """Widening, defaults to least upper bound (i.e. join)."""
        return self | other
