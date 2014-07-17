import collections
import itertools

from soap.expression import (
    BinaryBoolExpr, LESS_OP, GREATER_OP, LESS_EQUAL_OP, GREATER_EQUAL_OP,
    EQUAL_OP, NOT_EQUAL_OP
)


constraint_negate_dict = {
    LESS_OP: GREATER_EQUAL_OP,
    LESS_EQUAL_OP: GREATER_OP,
    GREATER_OP: LESS_EQUAL_OP,
    GREATER_EQUAL_OP: LESS_OP,
    EQUAL_OP: NOT_EQUAL_OP,
    NOT_EQUAL_OP: EQUAL_OP,
}


class Constraint(object):
    def __init__(self, variable, relation, value):
        super().__init__()
        self.variable = variable
        self.relation = relation
        self.value = value

    def __invert__(self):
        relation = constraint_negate_dict[self.relation]
        return self.__class__(self.variable, relation, self.value)

    def bool_expr(self):
        return BinaryBoolExpr(self.relation, self.variable, self.value)

    def __str__(self):
        return str(self.bool_expr())

    def __repr__(self):
        return '{cls}({var!r}, {rel!r}, {val!r})'.format(
            cls=self.__class__.__name__,
            var=self.variable, rel=self.relation, val=self.value)

    def __eq__(self, other):
        return self.bool_expr() == other.bool_expr()

    def __hash__(self):
        return hash(self.bool_expr())


class ConstraintSet(collections.MutableSet):
    def __init__(self, iterable=None):
        super().__init__()
        iterable = iterable or []
        disjunctions = set()
        for e in iterable:
            if isinstance(e, Constraint):
                e = {e}
            if isinstance(e, set):
                e = frozenset(e)
            if isinstance(e, frozenset):
                disjunctions.add(e)
                continue
            raise TypeError(
                'Cannot add {} into a ConstraintSet object.'.format(e))
        self.constraints = self._reduce(disjunctions)

    def _reduce(self, iterable):
        reduced = []
        for more in iterable:
            if any(fewer <= more for fewer in iterable if fewer != more):
                continue
            reduced.append(more)
        return set(reduced)

    def __contains__(self, item):
        return item in self.constraints

    def __iter__(self):
        return iter(self.constraints)

    def __len__(self):
        return len(self.constraints)

    def add(self, item):
        return self.constraints.add(item)

    def discard(self, item):
        return self.constraints.discard(item)

    def __lt__(self, other):
        return self.constraints < other.constraints

    def __or__(self, other):
        other = {other} if isinstance(other, Constraint) else other.constraints
        return self.__class__(self.constraints | other)

    def __and__(self, other):
        other = {other} if isinstance(other, Constraint) else other.constraints
        new_cstr_list = [
            self_cstr | other_cstr
            for self_cstr, other_cstr in itertools.product(self, other)]
        return self.__class__(new_cstr_list)

    def __invert__(self):
        conjunctions = [ConstraintSet(~e for e in c) for c in self.constraints]
        constraint_set = None
        for c in conjunctions:
            if constraint_set is None:
                constraint_set = c
            else:
                constraint_set = constraint_set & c
        return constraint_set

    def __str__(self):
        conjunctions = [
            '({})'.format(' ∧ '.join(str(e) for e in c))
            for c in self.constraints]
        return ' ∨ '.join(conjunctions)

    def __repr__(self):
        return '{cls}({cstr})'.format(
            cls=self.__class__.__name__, cstr=self.constraints)
