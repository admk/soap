import unittest

from soap.expression import expression_factory, operators, Variable, Subscript
from soap.semantics import IntegerInterval, ErrorSemantics
from soap.program import (
    AssignFlow, IdentityFlow, IfFlow, WhileFlow, InputFlow, OutputFlow,
    CompositionalFlow
)
from soap.parser.program import parse


class TestProgramParser(unittest.TestCase):
    def setUp(self):
        self.x = Variable('x')
        self.y = Variable('y')
        self.z = Variable('z')
        self.i1 = IntegerInterval(1)
        self.i2 = IntegerInterval(2)
        self.i3 = IntegerInterval(3)

    def test_compound_boolean_expression(self):
        bool_expr_1 = expression_factory(
            operators.UNARY_NEGATION_OP, expression_factory(
                operators.LESS_OP, self.x, self.i3))
        bool_expr_2 = expression_factory(
            operators.NOT_EQUAL_OP, self.y, self.i1)
        bool_expr = expression_factory(
            operators.AND_OP, bool_expr_1, bool_expr_2)
        # FIXME the parser is not really meant to parse expressions
        # so parens are added to make sure it gets parsed correctly
        self.assertEqual(parse('(not x < 3 and y != 1)'), bool_expr)

    def test_operator_precedence(self):
        neg_y = expression_factory(operators.UNARY_SUBTRACT_OP, self.y)

        expr = expression_factory(
            operators.ADD_OP, self.x,
            expression_factory(operators.MULTIPLY_OP, neg_y, self.z))
        self.assertEqual(parse('x + -y * z'), expr)

        expr = expression_factory(
            operators.MULTIPLY_OP,
            expression_factory(operators.ADD_OP, self.x, neg_y),
            self.z)
        self.assertEqual(parse('(x + -y) * z'), expr)

    def test_select_expression(self):
        expr = expression_factory(
            operators.TERNARY_SELECT_OP,
            expression_factory(operators.LESS_OP, self.x, self.i3),
            expression_factory(operators.ADD_OP, self.y, self.i1),
            expression_factory(operators.MULTIPLY_OP, self.y, self.i2))
        self.assertEqual(parse('x < 3 ? y + 1 : y * 2'), expr)

    def test_variable_subscript(self):
        expr = expression_factory(
            operators.INDEX_ACCESS_OP, self.x, Subscript(self.i1))
        self.assertEqual(parse('x[1]'), expr)

        expr = expression_factory(
            operators.INDEX_ACCESS_OP, self.x,
            Subscript(expression_factory(operators.ADD_OP, self.y, self.i1)))
        self.assertEqual(parse('x[y + 1]'), expr)

        expr = expression_factory(
            operators.INDEX_ACCESS_OP, self.x, Subscript(self.y, self.i1))
        self.assertEqual(parse('x[y, 1]'), expr)

        expr = expression_factory(
            operators.INDEX_ACCESS_OP, self.x,
            Subscript(expression_factory(
                operators.INDEX_ACCESS_OP, self.y, Subscript(self.i1))))
        self.assertEqual(parse('x[y[1]]'), expr)

    def test_skip_statement(self):
        self.assertEqual(parse('skip;'), IdentityFlow())

    def test_assign_statement(self):
        expr = expression_factory(
            operators.ADD_OP, self.y, self.i1)
        flow = AssignFlow(self.x, expr)
        self.assertEqual(parse('x := y + 1;'), flow)

    def test_if_statement(self):
        bool_expr = expression_factory(operators.LESS_OP, self.x, self.i3)
        assign_flow = AssignFlow(self.y, self.x)
        flow = IfFlow(bool_expr, assign_flow, IdentityFlow())
        self.assertEqual(parse('if (x < 3) (y := x;);'), flow)
        self.assertEqual(parse('if (x < 3) (y := x;) (skip;);'), flow)

    def test_while_statement(self):
        bool_expr = expression_factory(operators.LESS_OP, self.x, self.i3)
        assign_flow = AssignFlow(self.y, self.x)
        flow = WhileFlow(bool_expr, assign_flow)
        self.assertEqual(parse('while (x < 3) (y := x;);'), flow)

    def test_input_statement(self):
        flow = InputFlow({self.x: IntegerInterval([1, 2])})
        self.assertEqual(parse('input (x: [1, 2]);'), flow)
        flow = InputFlow({
            self.x: self.i1,
            self.y: ErrorSemantics([3.0, 4.0]),
            self.z: ErrorSemantics([5, 6], [0, 0]),
        })
        parsed_flow = parse(
            'input (x: 1, y: [3.0, 4.0], z: [5.0, 6.0][0, 0]);')
        self.assertEqual(parsed_flow, flow)

    def test_output_statement(self):
        flow = OutputFlow([self.x])
        self.assertEqual(parse('output (x);'), flow)
        flow = OutputFlow(Variable(x) for x in ['x', 'y', 'z'])
        self.assertEqual(parse('output (x, y, z);'), flow)

    def test_compound_statement(self):
        flow = CompositionalFlow([IdentityFlow(), AssignFlow(self.x, self.y)])
        self.assertEqual(parse('skip; x := y;'), flow)
