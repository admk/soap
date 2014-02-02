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

    def decorate_pre_conditional(func):
        @wraps(func)
        def pre_conditional(self, expr, annotation):
            true_state, false_state = func(self, expr, annotation)
            logger.debug(
                '⟦[{expr}]{annotation}⟧{state} --split-→ ({true}, {false})'
                .format(
                    expr=expr, annotation=superscript(annotation),
                    state=self, true=true_state, false=false_state))
            return true_state, false_state
        return pre_conditional

    def decorate_post_conditional(func):
        @wraps(func)
        def post_conditional(self, expr, true_state, false_state, annotation):
            state = func(self, expr, true_state, false_state, annotation)
            logger.debug(
                '⟦[{expr}]{annotation}⟧{prev}: '
                '({true}, {false}) --join-→ {next}'.format(
                    prev=self, expr=expr, annotation=superscript(annotation),
                    true=true_state, false=false_state, next=state))
            return state
        return post_conditional

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
    cls.pre_conditional = decorate_pre_conditional(cls.pre_conditional)
    cls.post_conditional = decorate_post_conditional(cls.post_conditional)
    cls.join = decorate_join(cls.join)
    cls.le = decorate_le(cls.le)


class BaseState(object):
    """Base state for all program states."""
    __slots__ = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _decorate(self.__class__)

    def assign(self, var, expr, annotation):
        """Makes an assignment and returns a new state object."""
        raise NotImplementedError

    def pre_conditional(self, expr, cond, annotation):
        """Imposes a conditional on the state, returns a 2-tuple of states,
        respectively represent true and false states."""
        raise NotImplementedError

    def post_conditional(self, expr, true_state, false_state, annotation):
        """Joins true and false states, return a new state."""
        raise NotImplementedError

    def is_fixpoint(self, other):
        """Fixpoint test, defaults to equality."""
        return self == other

    def widen(self, other):
        """Widening, defaults to least upper bound (i.e. join)."""
        return self | other
