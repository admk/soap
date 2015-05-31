import unittest

from soap.datatype import int_type, IntegerArrayType
from soap.expression import (
    Variable, BinaryArithExpr, BinaryBoolExpr, operators, UnaryArithExpr,
    SelectExpr, FixExpr, AccessExpr, UpdateExpr, Subscript,
)
from soap.semantics.error import IntegerInterval
from soap.semantics.functions.label import LabelGenerator
from soap.semantics.label import LabelContext, LabelSemantics
from soap.semantics.state.box import BoxState
from soap.semantics.state.meta import MetaState
from soap.semantics.linalg import IntegerIntervalArray


class TestLabel(unittest.TestCase):
    def setUp(self):
        self.context = LabelContext('test_context')
        mat = IntegerIntervalArray([1, 2, 3, 4])
        self.x = Variable('x', int_type)
        self.y = Variable('y', int_type)
        self.z = Variable('z', IntegerArrayType([4]))
        self.state = BoxState({
            self.x: [1, 2],
            self.y: 3,
            self.z: mat,
        })
        self.x_label = self.context.Label(
            self.x, IntegerInterval([1, 2]), None)
        self.y_label = self.context.Label(self.y, IntegerInterval(3), None)
        self.z_label = self.context.Label(self.z, mat, None)

    def label(self, expr, state=None):
        state = state or self.state
        return LabelGenerator(self.context).execute(expr, state)

    def compare(self, expr, test_labsem):
        labsem = self.label(expr)
        self.assertEqual(test_labsem, labsem)
        self.assertEqual(test_labsem.expr(), expr)
        self.assertEqual(labsem.expr(), expr)

    def test_numeral(self):
        expr = IntegerInterval(1)
        label = self.context.Label(expr, expr, None)
        test_value = LabelSemantics(label, {label: expr})
        self.compare(expr, test_value)

    def test_variable(self):
        expr = self.x
        test_value = LabelSemantics(self.x_label, {self.x_label: expr})
        self.compare(expr, test_value)

    def test_UnaryArithExpr(self):
        expr = UnaryArithExpr(operators.UNARY_SUBTRACT_OP, self.x)
        label_expr = UnaryArithExpr(
            operators.UNARY_SUBTRACT_OP, self.x_label)
        label = self.context.Label(expr, IntegerInterval([-2, -1]), None)
        env = {label: label_expr, self.x_label: self.x}
        test_value = LabelSemantics(label, env)
        self.compare(expr, test_value)

    def test_BinaryArithExpr(self):
        expr = BinaryArithExpr(operators.ADD_OP, self.x, self.y)
        label_expr = BinaryArithExpr(
            operators.ADD_OP, self.x_label, self.y_label)
        label = self.context.Label(expr, IntegerInterval([4, 5]), None)
        env = {
            label: label_expr,
            self.x_label: self.x,
            self.y_label: self.y,
        }
        test_value = LabelSemantics(label, env)
        self.compare(expr, test_value)

    def bool_expr(self):
        expr = BinaryBoolExpr(operators.LESS_OP, self.x, self.y)
        label_expr = BinaryBoolExpr(
            operators.LESS_OP, self.x_label, self.y_label)
        # FIXME bound for bool_expr does not make sense
        label = self.context.Label(expr, IntegerInterval([-2, -1]), None)
        return label, expr, label_expr

    def test_BinaryBoolExpr(self):
        label, expr, label_expr = self.bool_expr()
        env = {
            label: label_expr,
            self.x_label: self.x,
            self.y_label: self.y,
        }
        test_value = LabelSemantics(label, env)
        self.compare(expr, test_value)

    def test_AccessExpr(self):
        subscript = Subscript(self.y)
        expr = AccessExpr(self.z, subscript)
        label_subscript_expr = Subscript(self.y_label)
        subscript_label = self.context.Label(
            subscript, IntegerIntervalArray([self.state[self.y]]), None)
        label_expr = AccessExpr(self.z_label, subscript_label)
        label = self.context.Label(expr, IntegerInterval(4), None)
        env = {
            label: label_expr,
            subscript_label: label_subscript_expr,
            self.y_label: self.y,
            self.z_label: self.z,
        }
        test_value = LabelSemantics(label, env)
        self.compare(expr, test_value)

    def test_UpdateExpr(self):
        subscript = Subscript(self.y)
        expr = UpdateExpr(self.z, subscript, self.x)
        label_subscript_expr = Subscript(self.y_label)
        subscript_label = self.context.Label(
            subscript, IntegerIntervalArray([self.state[self.y]]), None)
        label_expr = UpdateExpr(self.z_label, subscript_label, self.x_label)
        new_bound = IntegerIntervalArray([1, 2, 3, IntegerInterval([1, 2])])
        label = self.context.Label(expr, new_bound, None)
        env = {
            label: label_expr,
            subscript_label: label_subscript_expr,
            self.x_label: self.x,
            self.y_label: self.y,
            self.z_label: self.z,
        }
        test_value = LabelSemantics(label, env)
        self.compare(expr, test_value)

    def test_SelectExpr(self):
        bool_label, bool_expr, bool_label_expr = self.bool_expr()
        expr = SelectExpr(bool_expr, self.x, self.y)
        label_expr = SelectExpr(bool_label, self.x_label, self.y_label)
        label = self.context.Label(expr, IntegerInterval([1, 2]), None)
        env = {
            label: label_expr,
            bool_label: bool_label_expr,
            self.x_label: self.x,
            self.y_label: self.y,
        }
        test_value = LabelSemantics(label, env)
        self.compare(expr, test_value)

    def test_FixExpr(self):
        init_state = MetaState({self.x: IntegerInterval(0)})
        init_label, init_env = self.label(init_state)

        invar = BoxState({self.x: IntegerInterval([0, 4])})
        end_invar = BoxState({self.x: IntegerInterval([1, 5])})

        loop_state = MetaState({
            self.x: BinaryArithExpr(
                operators.ADD_OP, self.x, IntegerInterval(1)),
        })
        loop_label, loop_env = self.label(loop_state, invar)

        bool_expr = BinaryBoolExpr(
            operators.LESS_OP, self.x, IntegerInterval(5))
        bool_labsem = self.label(bool_expr, end_invar)
        bool_label, _ = bool_labsem

        expr = FixExpr(bool_expr, loop_state, self.x, init_state)

        bound = IntegerInterval(5)
        label = self.context.Label(expr, bound, invar)
        label_expr = FixExpr(bool_labsem, loop_env, self.x, init_env)
        env = {label: label_expr}
        test_value = LabelSemantics(label, env)
        self.compare(expr, test_value)

    def test_MetaState(self):
        meta_state = MetaState({self.x: self.x, self.y: self.y})
        env = {
            self.x: self.x_label,
            self.y: self.y_label,
            self.x_label: self.x,
            self.y_label: self.y,
        }
        bound = BoxState(x=self.state[self.x], y=self.state[self.y])
        label = self.context.Label(meta_state, bound, None)
        test_value = LabelSemantics(label, env)
        self.compare(meta_state, test_value)


"""
class TestStitch(TestLabel):
    def compare(self, expr, test_labsem):
        test_expr = stitch(test_labsem)
        self.assertEqual(test_expr, expr)
"""
