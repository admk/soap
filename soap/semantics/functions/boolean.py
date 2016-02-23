import collections
import itertools
import math

from soap.common.cache import cached
from soap.context import context
from soap.expression import (
    BinaryBoolExpr, is_variable, LESS_OP, GREATER_OP, LESS_EQUAL_OP,
    GREATER_EQUAL_OP, EQUAL_OP, NOT_EQUAL_OP, UNARY_NEGATION_OP, AND_OP,
    OR_OP, COMPARISON_OPERATORS, BINARY_OPERATORS, COMPARISON_NEGATE_DICT,
    COMPARISON_MIRROR_DICT,
)
from soap.lattice import join, meet
from soap.semantics.error import (
    inf, ulp, mpz_type, mpfr_type,
    IntegerInterval, FloatInterval, ErrorSemantics
)


def _rhs_eval(expr, state):
    from soap.semantics.functions.arithmetic import arith_eval
    bound = arith_eval(expr, state)
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
        'Evaluation returns an unrecognized object: %r' % bound)


def _contract(op, dtype, bmin, bmax):
    if op not in [LESS_OP, GREATER_OP]:
        return bmin, bmax
    if dtype == IntegerInterval:
        bmin += 1
        bmax -= 1
    elif dtype == FloatInterval:
        bmin += ulp(bmin)
        bmax -= ulp(bmax)
    else:
        raise TypeError('Unknown type {}'.format(dtype))
    return bmin, bmax


def _constraint(op, cond, dtype, bmin, bmax):
    op = COMPARISON_NEGATE_DICT[op] if not cond else op
    bmin, bmax = _contract(op, dtype, bmin, bmax)
    if op == EQUAL_OP:
        return dtype([bmin, bmax])
    if op == NOT_EQUAL_OP:
        return dtype([-inf, inf])
    if op in [LESS_OP, LESS_EQUAL_OP]:
        return dtype([-inf, bmax])
    if op in [GREATER_OP, GREATER_EQUAL_OP]:
        return dtype([bmin, inf])
    raise ValueError('Unknown boolean operator {}'.format(op))


def _conditional(op, var, expr, state, cond):
    value = state[var]
    dtype = type(value)
    if dtype == ErrorSemantics:
        dtype = FloatInterval
    bound = _rhs_eval(expr, state)

    if state.is_bottom():
        return var, dtype(bottom=True)
    if bound.is_bottom():
        raise ValueError('Cannot evaluate {} with {}'.format(expr, state))

    bmin, bmax = bound.min, bound.max
    if isinstance(value, IntegerInterval) and \
       isinstance(bound, FloatInterval):
        bmin, bmax = int(math.ceil(bmin)), int(math.floor(bmax))
        op_map = {LESS_OP: LESS_EQUAL_OP, GREATER_OP: GREATER_EQUAL_OP}
        op = op_map.get(op, op)
    cstr = _constraint(op, cond, dtype, bmin, bmax)
    if isinstance(cstr, FloatInterval):
        cstr = ErrorSemantics(cstr, FloatInterval(top=True))
    cstr &= state[var]
    bot = isinstance(cstr, ErrorSemantics) and cstr.v.is_bottom()
    bot = bot or cstr.is_bottom()
    if bot:
        return var, cstr.__class__(bottom=True)
    return var, cstr


def _comparison_eval(expr, state):
    op = expr.op
    a1, a2 = expr.args
    args_swap_list = [(op, a1, a2), (COMPARISON_MIRROR_DICT[op], a2, a1)]
    split_list = []
    for cond in True, False:
        cstr_list = []
        for cond_op, cond_var, cond_expr in args_swap_list:
            if not is_variable(cond_var):
                continue
            cstr = _conditional(cond_op, cond_var, cond_expr, state, cond)
            cstr_list.append(cstr)
        if any(cstr.is_bottom() for _, cstr in cstr_list):
            split = state.empty()
        else:
            split = state
            for var, cstr in cstr_list:
                split = split.immu_update(var, cstr)
        split_list.append(split)
    return tuple(split_list)


class _Constraints(collections.MutableSet):
    def __init__(self, iterable=None):
        super().__init__()
        iterable = iterable or []
        if isinstance(iterable, BinaryBoolExpr):
            iterable = [iterable]
        disjunctions = set()
        for e in iterable:
            if isinstance(e, BinaryBoolExpr):
                e = {e}
            if isinstance(e, set):
                e = frozenset(e)
            if isinstance(e, frozenset):
                disjunctions.add(e)
                continue
            raise TypeError('Do not know how to add {!r}.'.format(e))
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

    @staticmethod
    def _other(other):
        if isinstance(other, BinaryBoolExpr):
            return {other}
        return other.constraints

    def __or__(self, other):
        return self.__class__(self.constraints | self._other(other))

    def __and__(self, other):
        other = self._other(other)
        new_cstr_list = [
            self_cstr | other_cstr
            for self_cstr, other_cstr in itertools.product(self, other)]
        return self.__class__(new_cstr_list)

    @staticmethod
    def _negate(expr):
        return BinaryBoolExpr(COMPARISON_NEGATE_DICT[expr.op], *expr.args)

    def __invert__(self):
        conjunctions = [
            self.__class__(self._negate(e) for e in c)
            for c in self.constraints]
        constraint_set = None
        for c in conjunctions:
            if constraint_set is None:
                constraint_set = c
            else:
                constraint_set = constraint_set & c
        return constraint_set

    def __str__(self):
        conjunctions = [
            '({})'.format(' & '.join(str(e) for e in c))
            for c in self.constraints]
        return ' | '.join(conjunctions)

    def __repr__(self):
        return '{cls}({cstr})'.format(
            cls=self.__class__.__name__, cstr=self.constraints)


_binary_operator_construct_map = {
    AND_OP: lambda a1, a2: a1 & a2,
    OR_OP: lambda a1, a2: a1 | a2,
}


@cached
def construct(expr):
    op = expr.op
    if op in COMPARISON_OPERATORS:
        return _Constraints(expr)
    if op in BINARY_OPERATORS:
        a1, a2 = expr.args
        a1, a2 = construct(a1), construct(a2)
        return _binary_operator_construct_map[op](a1, a2)
    if op == UNARY_NEGATION_OP:
        return ~expr.a
    TypeError(
        'Do not know how to construct constraints from {}'.format(expr))


@cached
def _bool_transform(expr):
    from soap.transformer.utils import closure
    bool_vars = []
    bool_expr_set = set()
    transformed = closure(
        expr, depth=context.small_depth, no_bool=False,
        steps=context.small_steps)
    for expr in sorted(transformed, key=hash):
        a1, a2 = expr.args
        if is_variable(a1) and a1 not in bool_vars:
            bool_vars.append(a1)
            bool_expr_set.add(expr)
        if is_variable(a2) and a2 not in bool_vars:
            bool_vars.append(a2)
            bool_expr_set.add(expr)
    return bool_expr_set


@cached
def bool_eval(expr, state):
    if state.is_bottom():
        return state, state
    constraints = construct(expr)
    true_list, false_list = [], []
    for cstr in constraints:
        cstr_list = []
        for cmp_expr in cstr:
            cmp_eval_list = [
                _comparison_eval(cmp_expr, state)
                for cmp_expr in _bool_transform(cmp_expr)]
            cstr_list += cmp_eval_list
        if not cstr_list:
            # empty, don't know how to constraint values
            return state, state
        true, false = zip(*cstr_list)
        true_list.append(meet(true))
        false_list.append(join(false))
    return join(true_list), meet(false_list)
