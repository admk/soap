import unittest

from soap.datatype import auto_type, int_type, real_type, function_type
from soap.expression import expression_factory, operators, Variable, Subscript
from soap.semantics import IntegerInterval, ErrorSemantics
from soap.program import (
    AssignFlow, IdentityFlow, IfFlow, WhileFlow, FunctionFlow, ReturnFlow,
    CompositionalFlow
)
from soap.parser import stmt_parse, expr_parse, parse


class Base(unittest.TestCase):
    def setUp(self):
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


class TestStatementParser(Base):
    def setUp(self):
        super().setUp()
        self.stmt_parse = lambda prog: stmt_parse(prog, self.decl)

    def test_skip_statement(self):
        self.assertEqual(stmt_parse('skip;'), IdentityFlow())

    def test_assign_statement(self):
        expr = expression_factory(
            operators.ADD_OP, self.y, self.i1)
        flow = AssignFlow(self.x, expr)
        self.assertEqual(self.stmt_parse('x = y + 1;'), flow)

    def test_if_statement(self):
        bool_expr = expression_factory(operators.LESS_OP, self.x, self.i3)
        assign_flow = AssignFlow(self.y, self.x)
        flow = IfFlow(bool_expr, assign_flow, IdentityFlow())
        self.assertEqual(self.stmt_parse('if (x < 3) {y = x;}'), flow)
        self.assertEqual(
            self.stmt_parse('if (x < 3) {y = x;} else {skip;}'), flow)

    def test_while_statement(self):
        bool_expr = expression_factory(operators.LESS_OP, self.x, self.i3)
        assign_flow = AssignFlow(self.y, self.x)
        flow = WhileFlow(bool_expr, assign_flow)
        self.assertEqual(self.stmt_parse('while (x < 3) {y = x;}'), flow)

    def test_compound_statement(self):
        flow = CompositionalFlow([IdentityFlow(), AssignFlow(self.x, self.y)])
        self.assertEqual(self.stmt_parse('skip; x = y;'), flow)

    def test_return_statement(self):
        flow = ReturnFlow([self.x])
        self.assertEqual(self.stmt_parse('return x;'), flow)
        flow = ReturnFlow([self.x, self.y])
        self.assertEqual(self.stmt_parse('return x, y;'), flow)


class TestProgramParser(Base):
    def setUp(self):
        super().setUp()
        self.x = Variable('x', int_type)
        self.y = Variable('y', real_type)
        self.z = Variable('z', real_type)

    def test_function(self):
        expr = expression_factory(
            operators.ADD_OP, expression_factory(
                operators.ADD_OP, self.x, self.y), self.z)
        body = CompositionalFlow([
            AssignFlow(self.z, expr), ReturnFlow([self.z]),
        ])
        flow = FunctionFlow(Variable('main', function_type), [
            (self.x, self.i1),
            (self.y, ErrorSemantics([3.0, 4.0])),
            (self.z, ErrorSemantics([5, 6], [0, 0])),
        ], body)
        prog = """
            def main(int x: 1, real y: [3.0, 4.0], real z: [5.0, 6.0][0, 0]) {
                z = x + y + z;
                return z;
            }
            """
        parsed_flow = parse(prog)
        self.assertEqual(flow, parsed_flow)
