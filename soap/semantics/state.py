"""
.. module:: soap.semantics.state
    :synopsis: Program states.
"""
from functools import wraps

from soap import logger

from soap.expr import LESS_OP, GREATER_OP, LESS_EQUAL_OP, GREATER_EQUAL_OP
from soap.lattice import denotational, map
from soap.semantics import Interval, IntegerInterval, FloatInterval, inf


def _decorate(cls):
    def decorate_assign(func):
        @wraps(func)
        def assign(self, var, expr):
            state = func(self, var, expr)
            logger.debug(
                '⟦' + str(var) + ' := ' + str(expr) + '⟧:',
                str(self), '→', str(state))
            return state
        return assign

    def decorate_conditional(func):
        @wraps(func)
        def conditional(self, expr, cond):
            state = func(self, expr, cond)
            logger.debug(
                '⟦' + str(expr if cond else ~expr) + '⟧:',
                str(self), '→', str(state))
            return state
        return conditional

    def decorate_join(func):
        @wraps(func)
        def join(self, other):
            state = func(self, other)
            logger.debug(str(self) + ' ⊔ ' + str(other), '→', str(state))
            return state
        return join

    def decorate_le(func):
        @wraps(func)
        def le(self, other):
            b = func(self, other)
            logger.debug(str(self), '⊑' if b else '⋢', str(other))
            return b
        return le

    try:
        if cls == State or cls._state_decorated:
            return
    except AttributeError:
        cls._state_decorated = True
    cls.assign = decorate_assign(cls.assign)
    cls.conditional = decorate_conditional(cls.conditional)
    cls.join = decorate_join(cls.join)
    cls.le = decorate_le(cls.le)


class State(object):
    """Program state.

    This provides the base class of all denotational semantics-based state
    objects.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _decorate(self.__class__)

    def assign(self, var, expr):
        """Makes an assignment and returns a new state object."""
        mapping = dict(self)
        try:
            mapping[var] = expr.eval(self)
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
        if expr.eval(self) == cond:
            return self
        return self.__class__(bottom=True)


_negate_dict = {
    LESS_OP: GREATER_EQUAL_OP,
    LESS_EQUAL_OP: GREATER_OP,
    GREATER_OP: LESS_EQUAL_OP,
    GREATER_EQUAL_OP: LESS_OP,
}


class IntervalState(State, map(str, Interval)):
    """The traditional program analysis state object based on intervals.

    Supports only simple boolean expressions::
        <variable> <operator> <arithmetic expression>
    For example::
        x <= 3 * y.
    """
    def conditional(self, expr, cond):
        try:
            bound = expr.a2.eval(self)
        except AttributeError:  # expr.a2 is a constant
            if isinstance(expr.a2, int):
                bound = IntegerInterval(expr.a2)
            else:
                bound = FloatInterval(expr.a2)
        mapping = dict(self)
        op = expr.op
        if not cond:
            op = _negate_dict[op]
        if op in [LESS_OP, LESS_EQUAL_OP]:
            if op == LESS_OP and isinstance(bound, IntegerInterval):
                bound.max -= 1
            cstr = Interval([-inf, bound.max])
        elif op in [GREATER_OP, GREATER_EQUAL_OP]:
            if op == GREATER_OP and isinstance(bound, IntegerInterval):
                bound.min += 1
            cstr = Interval([bound.min, inf])
        else:
            raise ValueError('Unknown operator %s' % op)
        mapping[expr.a1] &= cstr
        return self.__class__(mapping)
