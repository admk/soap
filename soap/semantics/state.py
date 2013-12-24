"""
.. module:: soap.semantics.state
    :synopsis: Program states.
"""
from functools import wraps

from soap import logger
from soap.expression import (
    LESS_OP, GREATER_OP, LESS_EQUAL_OP, GREATER_EQUAL_OP,
    EQUAL_OP, NOT_EQUAL_OP, Expression, Variable, expression_factory
)
from soap.lattice import map
from soap.semantics.error import (
    inf, ulp, cast, mpz_type, mpfr_type,
    IntegerInterval, FloatInterval, ErrorSemantics
)
from soap.common import superscript
from soap.common.label import Identifier, Annotation, Label, Iteration


def _decorate(cls):
    def decorate_assign(func):
        @wraps(func)
        def assign(self, var, expr, annotation):
            state = func(self, var, expr, annotation)
            logger.debug(
                '⟦[{var} := {expr}]{annotation}⟧: {prev} → {next}'.format(
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
                '⟦[{expr}]{annotation}⟧: {prev} → {next}'.format(
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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _decorate(self.__class__)

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


class BoxState(BaseState, map(Variable, (IntegerInterval, ErrorSemantics))):
    """The program analysis domain object based on intervals and error
    semantics.
    """
    _negate_dict = {
        LESS_OP: GREATER_EQUAL_OP,
        LESS_EQUAL_OP: GREATER_OP,
        GREATER_OP: LESS_EQUAL_OP,
        GREATER_EQUAL_OP: LESS_OP,
        EQUAL_OP: NOT_EQUAL_OP,
        NOT_EQUAL_OP: EQUAL_OP,
    }

    def _cast_key(self, key):
        if isinstance(key, Variable):
            return key
        if isinstance(key, str):
            return Variable(key)
        raise TypeError('Do not know how to convert key {!r}'.format(key))

    def _cast_value(self, v=None, top=False, bottom=False):
        if top or bottom:
            return IntegerInterval(top=top, bottom=bottom)
        return cast(v)

    def eval(self, expr):
        """Evaluates an expression with state's mapping."""
        if isinstance(expr, Variable):
            return self[expr]
        if isinstance(expr, Expression):
            return expr.eval(self)
        if isinstance(expr, (IntegerInterval, FloatInterval, ErrorSemantics)):
            return expr
        if isinstance(expr, (mpz_type, mpfr_type)):
            return expr
        raise TypeError('Do not know how to evaluate {!r}'.format(expr))

    def assign(self, var, expr, annotation):
        mapping = dict(self)
        mapping[var] = self.eval(expr)
        return self.__class__(mapping)

    def conditional(self, expr, cond, annotation):
        """
        Supports only simple boolean expressions::
            <variable> <operator> <arithmetic expression>
        For example::
            x <= 3 * y.
        """
        def eval(expr):
            bound = self.eval(expr)
            if isinstance(bound, (int, mpz_type)):
                return IntegerInterval(bound)
            if isinstance(bound, (float, mpfr_type)):
                return FloatInterval(bound)
            if isinstance(bound, IntegerInterval):
                return bound
            if isinstance(bound, ErrorSemantics):
                # It cannot handle incorrect branching due to error in
                # evaluation of the expression.
                return bound.v
            raise TypeError(
                'Evaluation returns an object of unknown type %r' % bound)

        def contract(op, bound):
            if op not in [LESS_OP, GREATER_OP]:
                return bound.min, bound.max
            if isinstance(bound, IntegerInterval):
                bmin = bound.min + 1
                bmax = bound.max - 1
            elif isinstance(bound, FloatInterval):
                bmin = bound.min + ulp(bound.min)
                bmax = bound.max - ulp(bound.max)
            else:
                raise TypeError
            return bmin, bmax

        def constraint(op, bound):
            op = self._negate_dict[op] if not cond else op
            if bound.is_bottom():
                return bound
            bound_min, bound_max = contract(op, bound)
            if op == EQUAL_OP:
                return bound
            if op == NOT_EQUAL_OP:
                raise NotImplementedError
            if op in [LESS_OP, LESS_EQUAL_OP]:
                return bound.__class__([-inf, bound_max])
            if op in [GREATER_OP, GREATER_EQUAL_OP]:
                return bound.__class__([bound_min, inf])
            raise ValueError('Unknown boolean operator %s' % op)

        bound = eval(expr.a2)
        if isinstance(self[expr.a1], (FloatInterval, ErrorSemantics)):
            # Comparing floats
            bound = FloatInterval(bound)
        cstr = constraint(expr.op, bound)
        if isinstance(cstr, FloatInterval):
            cstr = ErrorSemantics(cstr, FloatInterval(top=True))
        cstr &= self[expr.a1]
        bot = isinstance(cstr, ErrorSemantics) and cstr.v.is_bottom()
        bot = bot or cstr.is_bottom()
        if bot:
            """Branch evaluates to false, because no possible values of the
            variable satisfies the constraint condition, it is safe to return
            *bottom* to denote an unreachable state. """
            return self.__class__(bottom=True)
        cstr_env = self.__class__(self)
        cstr_env[expr.a1] = cstr
        return cstr_env

    def is_fixpoint(self, other):
        """Checks if `self` is equal to `other` in the value ranges.

        For potential non-terminating loops, states are not the bottom element
        in the evaluation of loop statements even if a fixpoint is reached.
        This computation would result in a fixpoint of value ranges but
        the resulting error terms are strictly greater. Consequently for
        non-terminating loops the fixpoint for the error terms are always
        [-inf, inf] = ⊤. To gain any useful information about the program we
        wish to disregard the error terms and warn about non-termination.
        """
        if self.is_top() and other.is_top():
            return True
        if self.is_bottom() and other.is_bottom():
            return True
        non_bottom_keys = lambda d: set([k for k, v in d.items()
                                         if not v.is_bottom()])
        if non_bottom_keys(self) != non_bottom_keys(other):
            return False
        for k, v in self.items():
            u = other[k]
            if type(v) is not type(u):
                return False
            if isinstance(v, ErrorSemantics):
                u, v = u.v, v.v
            if u != v:
                return False
        return True

    def widen(self, other):
        """Simple widening operator, jumps to infinity if interval widens.

        self.widen(other) => self ∇ other
        """
        if self.is_top() or other.is_bottom():
            return self
        if self.is_bottom() or other.is_top():
            return other
        mapping = dict(self)
        for k, v in other.items():
            if k not in mapping:
                mapping[k] = v
            else:
                mapping[k] = mapping[k].widen(v)
        return self.__class__(mapping)


class ExpressionState(BaseState, map(Identifier, Expression)):
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
        """No widening is possible, simply return other."""
        return other
