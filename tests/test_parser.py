import unittest

from soap.expression import expression_factory, operators, Variable
from soap.semantics import IntegerInterval, ErrorSemantics
from soap.program import (
    AssignFlow, IdentityFlow, IfFlow, WhileFlow, InputFlow, OutputFlow,
    CompositionalFlow
)
from soap.parser.program import parse


class TestProgramParser(unittest.TestCase):
    def test_skip_statement(self):
        self.assertEqual(parse('skip;'), IdentityFlow())

    def test_assign_statement(self):
        expr = expression_factory(
            operators.ADD_OP, Variable('y'), IntegerInterval(1))
        flow = AssignFlow(Variable('x'), expr)
        self.assertEqual(parse('x := y + 1;'), flow)

    def test_if_statement(self):
        bool_expr = expression_factory(
            operators.LESS_OP, Variable('x'), IntegerInterval(3))
        assign_flow = AssignFlow(Variable('y'), Variable('x'))
        flow = IfFlow(bool_expr, assign_flow, IdentityFlow())
        self.assertEqual(parse('if (x < 3) (y := x;);'), flow)
        self.assertEqual(parse('if (x < 3) (y := x;) (skip;);'), flow)

    def test_compound_boolean_expression(self):
        bool_expr_1 = expression_factory(
            operators.LESS_OP, Variable('x'), IntegerInterval(3))
        bool_expr_2 = expression_factory(
            operators.NOT_EQUAL_OP, Variable('y'), IntegerInterval(1))
        bool_expr = expression_factory(
            operators.AND_OP, bool_expr_1, bool_expr_2)
        flow = IfFlow(bool_expr, IdentityFlow(), IdentityFlow())
        self.assertEqual(parse('if (x < 3 and y != 1) (skip;);'), flow)

    def test_while_statement(self):
        bool_expr = expression_factory(
            operators.LESS_OP, Variable('x'), IntegerInterval(3))
        assign_flow = AssignFlow(Variable('y'), Variable('x'))
        flow = WhileFlow(bool_expr, assign_flow)
        self.assertEqual(parse('while (x < 3) (y := x;);'), flow)

    def test_input_statement(self):
        flow = InputFlow({Variable('x'): IntegerInterval([1, 2])})
        self.assertEqual(parse('input (x: [1, 2]);'), flow)
        flow.inputs.update({
            Variable('y'): ErrorSemantics([3.0, 4.0]),
            Variable('z'): ErrorSemantics([5, 6], [0, 0]),
        })
        parsed_flow = parse(
            'input (x: [1, 2], y: [3.0, 4.0], z: [5.0, 6.0][0, 0]);')
        self.assertEqual(parsed_flow, flow)

    def test_output_statement(self):
        flow = OutputFlow([Variable('x')])
        self.assertEqual(parse('output (x);'), flow)
        flow = OutputFlow(Variable(x) for x in ['x', 'y', 'z'])
        self.assertEqual(parse('output (x, y, z);'), flow)

    def test_compound_statement(self):
        flow = CompositionalFlow(
            [IdentityFlow(), AssignFlow(Variable('x'), Variable('y'))])
        self.assertEqual(parse('skip; x := y;'), flow)
