from soap.common.cache import cached
from soap.expression import operators
from soap.expression.arithmetic import BinaryArithExpr


class LinkExpr(BinaryArithExpr):
    __slots__ = ()

    def __init__(self, a1=None, a2=None, top=False, bottom=False):
        super().__init__(operators.LINK_OP, a1, a2, top=top, bottom=bottom)

    @property
    def target_expr(self):
        return self.a1

    @property
    def meta_state(self):
        return self.a2

    @cached
    def eval(self, state):
        from soap.semantics.state.functions import (
            arith_eval, arith_eval_meta_state
        )
        state = arith_eval_meta_state(state, self.meta_state)
        return arith_eval(state, self.target_expr)

    def __str__(self):
        expr, state = self._args_to_str()
        return '{expr} % {state}'.format(expr=expr, state=state)

    def __repr__(self):
        return '{cls}({a1!r}, {a2!r})'.format(
            cls=self.__class__.__name__, a1=self.a1, a2=self.a2)


class FixExpr(BinaryArithExpr):
    """Fixpoint expression."""

    def __init__(self, a1=None, a2=None, top=False, bottom=False):
        super().__init__(operators.FIXPOINT_OP, a1, a2, top=top, bottom=bottom)

    @property
    def fix_var(self):
        return self.a1

    @property
    def fix_expr(self):
        return self.a2

    def _fixpoint(self, state):
        """
        Fixpoint computation, evaluates the expression.

        Because of the recursion nature of fixpoint expression, the code
        was expected to use tail recursion.  However note that it has been
        optimized into a loop.
        """
        from soap.semantics.error import Interval
        from soap.semantics.state.functions import (
            bool_eval, arith_eval_meta_state
        )

        fix_expr = self.fix_expr
        bool_expr = fix_expr.bool_expr
        loop_meta_state = fix_expr.true_expr.meta_state
        var = fix_expr.false_expr

        false_join_value = Interval(bottom=True)
        true_join_split = state.empty()
        true_state = state
        prev_true_state = None

        while true_state != prev_true_state:

            # split state into true and false splits
            true_split, false_split = bool_eval(true_state, bool_expr)
            # join true_split values observed, could be used for optimization
            # passes.
            true_join_split |= true_split

            # true_state gets executed with loop_meta_state, this computes a
            # new numerical state. this state is also intened for our next
            # iteration.
            # true_state = loop_meta_state * true_split
            prev_true_state = true_state
            true_state = arith_eval_meta_state(true_split, loop_meta_state)

            # get the value of the variable on evaluated to false
            # false_value = false_split[variable]
            false_join_value |= false_split[var]

        true_state._warn_non_termination(self)

        return {
            'eval_value': false_join_value,
            'true_join_split': true_join_split,
        }

    @cached
    def eval(self, state):
        return self._fixpoint(state)['eval_value']

    def __str__(self):
        return '{op}[{a1} ↦ {a2}]'.format(op=self.op, a1=self.a1, a2=self.a2)
