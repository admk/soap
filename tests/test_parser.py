import unittest

from soap.datatype import auto_type, int_type, real_type
from soap.expression import expression_factory, operators, Variable, Subscript
from soap.semantics import IntegerInterval, ErrorSemantics
from soap.program import (
    AssignFlow, IdentityFlow, IfFlow, WhileFlow, InputFlow, OutputFlow,
    CompositionalFlow
)
from soap.parser.program import parse, expr_parse


class TestProgramParser(unittest.TestCase):
    def setUp(self):
        self.x = Variable('x', auto_type)
        self.y = Variable('y', auto_type)
        self.z = Variable('z', auto_type)
        self.i1 = IntegerInterval(1)
        self.i2 = IntegerInterval(2)
        self.i3 = IntegerInterval(3)
        decl = {var.name: auto_type for var in (self.x, self.y, self.z)}
        self.parse = lambda prog: parse(prog, decl)

    def test_compound_boolean_expression(self):
        bool_expr_1 = expression_factory(
            operators.UNARY_NEGATION_OP, expression_factory(
                operators.LESS_OP, self.x, self.i3))
        bool_expr_2 = expression_factory(
            operators.NOT_EQUAL_OP, self.y, self.i1)
        bool_expr = expression_factory(
            operators.AND_OP, bool_expr_1, bool_expr_2)
        self.assertEqual(expr_parse('not x < 3 and y != 1'), bool_expr)

    def test_operator_precedence(self):
        neg_y = expression_factory(operators.UNARY_SUBTRACT_OP, self.y)

        expr = expression_factory(
            operators.ADD_OP, self.x,
            expression_factory(operators.MULTIPLY_OP, neg_y, self.z))
        self.assertEqual(expr_parse('x + -y * z'), expr)

        expr = expression_factory(
            operators.MULTIPLY_OP,
            expression_factory(operators.ADD_OP, self.x, neg_y),
            self.z)
        self.assertEqual(expr_parse('(x + -y) * z'), expr)

    def test_select_expression(self):
        expr = expression_factory(
            operators.TERNARY_SELECT_OP,
            expression_factory(operators.LESS_OP, self.x, self.i3),
            expression_factory(operators.ADD_OP, self.y, self.i1),
            expression_factory(operators.MULTIPLY_OP, self.y, self.i2))
        self.assertEqual(expr_parse('x < 3 ? y + 1 : y * 2'), expr)

    def test_variable_subscript(self):
        expr = expression_factory(
            operators.INDEX_ACCESS_OP, self.x, Subscript(self.i1))
        self.assertEqual(expr_parse('x[1]'), expr)

        expr = expression_factory(
            operators.INDEX_ACCESS_OP, self.x,
            Subscript(expression_factory(operators.ADD_OP, self.y, self.i1)))
        self.assertEqual(expr_parse('x[y + 1]'), expr)

        expr = expression_factory(
            operators.INDEX_ACCESS_OP, self.x, Subscript(self.y, self.i1))
        self.assertEqual(expr_parse('x[y, 1]'), expr)

        expr = expression_factory(
            operators.INDEX_ACCESS_OP, self.x,
            Subscript(expression_factory(
                operators.INDEX_ACCESS_OP, self.y, Subscript(self.i1))))
        self.assertEqual(expr_parse('x[y[1]]'), expr)

    def test_skip_statement(self):
        self.assertEqual(parse('skip;'), IdentityFlow())

    def test_assign_statement(self):
        expr = expression_factory(
            operators.ADD_OP, self.y, self.i1)
        flow = AssignFlow(self.x, expr)
        self.assertEqual(self.parse('x = y + 1;'), flow)

    def test_if_statement(self):
        bool_expr = expression_factory(operators.LESS_OP, self.x, self.i3)
        assign_flow = AssignFlow(self.y, self.x)
        flow = IfFlow(bool_expr, assign_flow, IdentityFlow())
        self.assertEqual(self.parse('if (x < 3) {y = x;}'), flow)
        self.assertEqual(self.parse('if (x < 3) {y = x;} else {skip;}'), flow)

    def test_while_statement(self):
        bool_expr = expression_factory(operators.LESS_OP, self.x, self.i3)
        assign_flow = AssignFlow(self.y, self.x)
        flow = WhileFlow(bool_expr, assign_flow)
        self.assertEqual(self.parse('while (x < 3) {y = x;}'), flow)

    def test_input_statement(self):
        flow = InputFlow({Variable('x', int_type): IntegerInterval([1, 2])})
        self.assertEqual(parse('input (int x: [1, 2]);'), flow)
        flow = InputFlow({
            Variable('x', int_type): self.i1,
            Variable('y', real_type): ErrorSemantics([3.0, 4.0]),
            Variable('z', real_type): ErrorSemantics([5, 6], [0, 0]),
        })
        parsed_flow = parse(
            'input (int x: 1, real y: [3.0, 4.0], real z: [5.0, 6.0][0, 0]);')
        self.assertEqual(parsed_flow, flow)

    def test_output_statement(self):
        flow = OutputFlow([self.x])
        self.assertEqual(self.parse('output (x);'), flow)
        flow = OutputFlow(Variable(x) for x in ['x', 'y', 'z'])
        self.assertEqual(self.parse('output (x, y, z);'), flow)

    def test_compound_statement(self):
        flow = CompositionalFlow([IdentityFlow(), AssignFlow(self.x, self.y)])
        self.assertEqual(self.parse('skip; x = y;'), flow)
