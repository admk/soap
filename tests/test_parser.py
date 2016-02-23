import nose
import unittest

from soap.datatype import auto_type, int_type, float_type, IntegerArrayType
from soap.expression import expression_factory, operators, Variable, Subscript
from soap.semantics import IntegerInterval, ErrorSemantics
from soap.program.flow import (
    AssignFlow, IfFlow, WhileFlow, ForFlow, CompositionalFlow,
    PragmaInputFlow, PragmaOutputFlow, ProgramFlow
)
from soap.parser import stmt_parse, expr_parse, parse


class Base(unittest.TestCase):
    def setUp(self):
        self.a = Variable('a', IntegerArrayType([10]))
        self.w = Variable('w', int_type)
        self.x = Variable('x', auto_type)
        self.y = Variable('y', auto_type)
        self.z = Variable('z', auto_type)
        self.i1 = IntegerInterval(1)
        self.i2 = IntegerInterval(2)
        self.i3 = IntegerInterval(3)
        self.decl = {var.name: auto_type for var in (self.x, self.y, self.z)}
        self.expr_parse = lambda expr: expr_parse(expr, self.decl)


class TestExpressionParser(Base):
    def test_compound_boolean_expression(self):
        bool_expr_1 = expression_factory(
            operators.UNARY_NEGATION_OP, expression_factory(
                operators.LESS_OP, self.x, self.i3))
        bool_expr_2 = expression_factory(
            operators.NOT_EQUAL_OP, self.y, self.i1)
        bool_expr = expression_factory(
            operators.AND_OP, bool_expr_1, bool_expr_2)
        self.assertEqual(expr_parse('!(x < 3) && y != 1'), bool_expr)

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

    def test_special_unary_arithmetic_expression(self):
        xpy = expression_factory(operators.ADD_OP, self.x, self.y)
        expr = expression_factory(operators.EXPONENTIATE_OP, xpy)
        self.assertEqual(expr_parse('exp(x + y)'), expr)

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
        self.assertEqual(expr_parse('x[y][1]'), expr)

        expr = expression_factory(
            operators.INDEX_ACCESS_OP, self.x,
            Subscript(expression_factory(
                operators.INDEX_ACCESS_OP, self.y, Subscript(self.i1))))
        self.assertEqual(expr_parse('x[y[1]]'), expr)


class TestStatementParser(Base):
    def setUp(self):
        super().setUp()
        self.stmt_parse = lambda prog: stmt_parse(prog, self.decl)

    def test_assign_statement(self):
        expr = expression_factory(
            operators.ADD_OP, self.y, self.i1)
        flow = AssignFlow(self.x, expr)
        self.assertEqual(self.stmt_parse('x = y + 1;'), flow)

    def test_boolean_assign_statement(self):
        raise nose.SkipTest  # can't bother with this now
        expr = expression_factory(
            operators.LESS_EQUAL_OP, self.y, self.i1)
        flow = AssignFlow(self.x, expr)
        self.assertEqual(self.stmt_parse('x = y < 1;'), flow)

    def test_declaration_assign_statement(self):
        flow = AssignFlow(self.w, self.i1)
        self.assertEqual(self.stmt_parse('int w = 1;'), flow)

    def test_declaration_statement(self):
        self.stmt_parse('int w;')
        self.stmt_parse('float a[10][10];')

    def test_operator_assign_statement(self):
        expr = expression_factory(
            operators.ADD_OP, self.x, self.i1)
        flow = AssignFlow(self.x, expr)
        self.assertEqual(self.stmt_parse('x += 1;'), flow)

    def test_increment_statement(self):
        expr = expression_factory(
            operators.ADD_OP, self.x, self.i1)
        flow = AssignFlow(self.x, expr)
        self.assertEqual(self.stmt_parse('x++;'), flow)

    def test_if_statement(self):
        bool_expr = expression_factory(operators.LESS_OP, self.x, self.i3)
        assign_flow_1 = AssignFlow(self.y, self.x)
        assign_flow_2 = AssignFlow(self.x, self.y)
        flow = IfFlow(bool_expr, assign_flow_1)
        self.assertEqual(self.stmt_parse('if (x < 3) {y = x;}'), flow)
        flow = IfFlow(bool_expr, assign_flow_1, assign_flow_2)
        self.assertEqual(
            self.stmt_parse('if (x < 3) {y = x;} else {x = y;}'), flow)

    def test_single_line_if_statement(self):
        bool_expr = expression_factory(operators.LESS_OP, self.x, self.i3)
        assign_flow_1 = AssignFlow(self.y, self.x)
        assign_flow_2 = AssignFlow(self.x, self.y)
        flow = IfFlow(bool_expr, assign_flow_1)
        self.assertEqual(self.stmt_parse('if (x < 3) y = x;'), flow)
        flow = IfFlow(bool_expr, assign_flow_1, assign_flow_2)
        self.assertEqual(
            self.stmt_parse('if (x < 3) y = x; else x = y;'), flow)

    def test_while_statement(self):
        bool_expr = expression_factory(operators.LESS_OP, self.x, self.i3)
        assign_flow = AssignFlow(self.y, self.x)
        flow = WhileFlow(bool_expr, assign_flow)
        self.assertEqual(self.stmt_parse('while (x < 3) {y = x;}'), flow)

    def test_single_line_while_statement(self):
        bool_expr = expression_factory(operators.LESS_OP, self.x, self.i3)
        assign_flow = AssignFlow(self.y, self.x)
        flow = WhileFlow(bool_expr, assign_flow)
        self.assertEqual(self.stmt_parse('while (x < 3) y = x;'), flow)

    def test_for_statement(self):
        bool_expr = expression_factory(operators.LESS_OP, self.x, self.i3)
        init_flow = AssignFlow(self.x, self.i1)
        incr_flow = AssignFlow(self.x, expression_factory(
            operators.ADD_OP, self.x, self.i1))
        assign_flow = AssignFlow(self.y, self.x)
        flow = ForFlow(init_flow, bool_expr, incr_flow, assign_flow)
        parsed_flow = self.stmt_parse('for (x = 1; x < 3; x = x + 1) {y = x;}')
        self.assertEqual(parsed_flow, flow)

    def test_single_line_for_statement(self):
        bool_expr = expression_factory(operators.LESS_OP, self.x, self.i3)
        init_flow = AssignFlow(self.x, self.i1)
        incr_flow = AssignFlow(self.x, expression_factory(
            operators.ADD_OP, self.x, self.i1))
        assign_flow = AssignFlow(self.y, self.x)
        flow = ForFlow(init_flow, bool_expr, incr_flow, assign_flow)
        parsed_flow = self.stmt_parse('for (x = 1; x < 3; x = x + 1) y = x;')
        self.assertEqual(parsed_flow, flow)

    def test_compound_statement(self):
        flow = CompositionalFlow(
            [AssignFlow(self.y, self.x), AssignFlow(self.x, self.y)])
        self.assertEqual(self.stmt_parse('y = x; x = y;'), flow)


class TestProgramParser(Base):
    def setUp(self):
        super().setUp()
        self.w = Variable('w', float_type)
        self.x = Variable('x', int_type)
        self.y = Variable('y', float_type)
        self.z = Variable('z', float_type)
        self.decl = {
            'x': int_type,
            'y': float_type,
            'z': float_type,
        }

    def test_full(self):
        expr = expression_factory(
            operators.ADD_OP, expression_factory(
                operators.ADD_OP, self.x, self.y), self.z)
        inputs = [
            (self.x, self.i1),
            (self.y, ErrorSemantics([3.0, 4.0], [0, 0])),
            (self.z, ErrorSemantics([5, 6], [0, 0])),
        ]
        outputs = [self.w]
        body = CompositionalFlow([
            PragmaInputFlow(inputs),
            PragmaOutputFlow(outputs),
            AssignFlow(self.w, expr),
        ])
        flow = ProgramFlow(body)
        prog = """
            #pragma soap input \
                int x=1, float y=[3.0, 4.0], float z=[5.0, 6.0][0, 0]
            #pragma soap output w
            float w = x + y + z;
            """
        parsed_flow = parse(prog)
        self.assertListEqual(list(parsed_flow.inputs.items()), inputs)
        self.assertListEqual(parsed_flow.outputs, outputs)
        self.assertEqual(parsed_flow, flow)
