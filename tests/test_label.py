import unittest

from soap.expression import (
    BinaryArithExpr, BinaryBoolExpr, operators, UnaryArithExpr, SelectExpr,
    AccessExpr, UpdateExpr, Subscript
)
from soap.parser.program import parse
from soap.semantics.error import IntegerInterval
from soap.semantics.functions.label import _label
from soap.semantics.label import LabelContext, LabelSemantics
from soap.semantics.state.box import BoxState
from soap.semantics.state.meta import MetaState
from soap.semantics.linalg import IntegerIntervalArray


class TestLabel(unittest.TestCase):
    def setUp(self):
        self.context = LabelContext('test_context')
        mat = IntegerIntervalArray([1, 2, 3, 4])
        self.state = BoxState(x=[1, 2], y=3, z=mat)
        self.x_label = self.context.Label(
            parse('x'), bound=IntegerInterval([1, 2]))
        self.y_label = self.context.Label(
            parse('y'), bound=IntegerInterval(3))
        self.z_label = self.context.Label(parse('z'), bound=mat)

    def label(self, expr):
        return _label(expr, self.state, self.context)

    def test_numeral(self):
        expr = IntegerInterval(1)
        label = self.context.Label(expr, bound=expr)
        test_value = LabelSemantics(label, {label: expr})
        value = self.label(expr)
        self.assertEqual(test_value, value)

    def test_variable(self):
        expr = parse('x')
        test_value = LabelSemantics(self.x_label, {self.x_label: expr})
        value = self.label(expr)
        self.assertEqual(test_value, value)

    def test_UnaryArithExpr(self):
        expr = parse('-x')
        label_expr = UnaryArithExpr(
            operators.UNARY_SUBTRACT_OP, self.x_label)
        label = self.context.Label(label_expr, bound=IntegerInterval([-2, -1]))
        env = {label: label_expr, self.x_label: parse('x')}
        test_value = LabelSemantics(label, env)
        value = self.label(expr)
        self.assertEqual(test_value, value)

    def test_BinaryArithExpr(self):
        expr = parse('x + y')
        label_expr = BinaryArithExpr(
            operators.ADD_OP, self.x_label, self.y_label)
        label = self.context.Label(label_expr, bound=IntegerInterval([4, 5]))
        env = {
            label: label_expr,
            self.x_label: parse('x'),
            self.y_label: parse('y'),
        }
        test_value = LabelSemantics(label, env)
        value = self.label(expr)
        self.assertEqual(test_value, value)

    def bool_expr(self):
        expr = BinaryBoolExpr(
            operators.LESS_OP, self.x_label, self.y_label)
        # FIXME bound for bool_expr does not make sense
        label = self.context.Label(expr, bound=IntegerInterval([-2, -1]))
        return expr, label

    def test_BinaryBoolExpr(self):
        expr = parse('(x < y)')
        label_expr, label = self.bool_expr()
        env = {
            label: label_expr,
            self.x_label: parse('x'),
            self.y_label: parse('y'),
        }
        test_value = LabelSemantics(label, env)
        value = self.label(expr)
        self.assertEqual(test_value, value)

    def test_AccessExpr(self):
        expr = parse('z[y]')
        label_subscript_expr = Subscript(self.y_label)
        subscript_label = self.context.Label(label_subscript_expr, None)
        label_expr = AccessExpr(self.z_label, subscript_label)
        label = self.context.Label(label_expr, IntegerInterval(4))
        env = {
            label: label_expr,
            subscript_label: label_subscript_expr,
            self.z_label: parse('z'),
            self.y_label: parse('y'),
        }
        test_value = LabelSemantics(label, env)
        value = self.label(expr)
        self.assertEqual(test_value, value)

    def test_UpdateExpr(self):
        expr = UpdateExpr(parse('z'), [parse('y')], parse('x'))
        label_subscript_expr = Subscript(self.y_label)
        subscript_label = self.context.Label(label_subscript_expr, None)
        label_expr = UpdateExpr(self.z_label, subscript_label, self.x_label)
        new_bound = IntegerIntervalArray([1, 2, 3, IntegerInterval([1, 2])])
        label = self.context.Label(label_expr, new_bound)
        env = {
            label: label_expr,
            subscript_label: label_subscript_expr,
            self.x_label: parse('x'),
            self.y_label: parse('y'),
            self.z_label: parse('z'),
        }
        test_value = LabelSemantics(label, env)
        value = self.label(expr)
        self.assertEqual(test_value, value)

    def test_SelectExpr(self):
        expr = parse('x < y ? x : y')
        bool_expr, bool_expr_label = self.bool_expr()
        label_expr = SelectExpr(bool_expr_label, self.x_label, self.y_label)
        label = self.context.Label(label_expr, bound=IntegerInterval([1, 2]))
        env = {
            label: label_expr,
            bool_expr_label: bool_expr,
            self.x_label: parse('x'),
            self.y_label: parse('y'),
        }
        test_value = LabelSemantics(label, env)
        value = self.label(expr)
        self.assertEqual(test_value, value)

    def test_FixExpr(self):
        ...

    def test_MetaState(self):
        meta_state = MetaState(x='x', y='y')
        env = {
            parse('x'): self.x_label,
            parse('y'): self.y_label,
            self.x_label: parse('x'),
            self.y_label: parse('y'),
        }
        label = self.context.Label(MetaState(env), None)
        test_value = LabelSemantics(label, env)
        value = self.label(meta_state)
        self.assertEqual(test_value, value)
