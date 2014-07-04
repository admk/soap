from parsimonious import Grammar, nodes

from soap.expression import expression_factory, operators
from soap.program import (
    IdentityFlow, AssignFlow, IfFlow, WhileFlow, CompositionalFlow
)


class _VisitorParser(nodes.NodeVisitor):
    grammar_file = 'soap/parser/program.grammar'

    def __init__(self):
        super().__init__()
        with open(self.grammar_file, 'r') as file:
            self.grammar = Grammar(file.read())

    def parse(self, program):
        tree = self.grammar.parse(program)
        return self.visit(tree)

    _lift_child = nodes.NodeVisitor.lift_child

    def _lift_first(self, node, children):
        return children[0]

    def _lift_children(self, node, children):
        return children

    def _lift_middle(self, node, children):
        _1, value, _2 = children
        return value

    def _lift_literal(self, node, children):
        return super()._lift_middle(node, children).literal

    def _lift_text(self, node, _):
        return node.text

    def _lift_dontcare(self, node, children):
        pass

    def generic_visit(self, node, children):
        if not node.expr_name:
            return children
        raise TypeError('Do not recognize node {!r}'.format(node))

    visit_statement = visit_single_statement = _lift_child

    def visit_compound_statement(self, node, children):
        single_statement, statement = children
        if not statement:
            return single_statement
        if isinstance(statement, CompositionalFlow):
            flows = statement.flows
        else:
            flows = [statement]
        flows = [single_statement] + flows
        return CompositionalFlow(flows)

    def visit_skip_statement(self, node, children):
        return IdentityFlow()

    def visit_assign_statement(self, node, children):
        var, assign_literal, expr, semicolon = children
        return AssignFlow(var, expr)

    visit_if_statement = _lift_first
    visit_if_block = _lift_child

    def visit_if_then_block(self, node, children):
        if_literal, bool_expr, true_flow = children
        return IfFlow(bool_expr, true_flow, IdentityFlow())

    def visit_if_else_block(self, node, children):
        if_flow, false_flow = children
        bool_expr = if_flow.bool_expr
        true_flow = if_flow.true_flow
        return IfFlow(bool_expr, true_flow, false_flow)

    def visit_while_statement(self, node, children):
        while_literal, bool_expr, loop_flow, semicolon = children
        return WhileFlow(bool_expr, loop_flow)

    visit_boolean_block = visit_code_block = _lift_middle

    def visit_boolean_expression(self, node, children):
        left_expr, op, right_expr = children
        return expression_factory(op, left_expr, right_expr)

    def _visit_concat_expr(self, node, children):
        expr, expr_list = children
        for each_expr in expr_list:
            each_op, each_factor = each_expr
            expr = expression_factory(each_op, expr, each_factor)
        return expr

    visit_arithmetic_expression = visit_factor = _visit_concat_expr
    visit_primary = _lift_child
    visit_parened = _lift_middle
    visit_sum_expr = visit_prod_expr = _lift_children

    def visit_unary_expr(self, node, children):
        op, primary = children
        if op == operators.SUBTRACT_OP:
            op = operators.UNARY_SUBTRACT_OP
        return expression_factory(op, primary)

    visit_skip_literal = visit_assign_literal = _lift_dontcare
    visit_if_literal = visit_while_literal = _lift_dontcare
    visit_left_paren = visit_right_paren = _lift_dontcare
    visit_semicolon = _lift_dontcare

    visit_boolean_operator = _lift_child
    visit_sum_operator = visit_prod_operator = _lift_child

    _operator_literal_map = {
        'add_literal': operators.ADD_OP,
        'sub_literal': operators.SUBTRACT_OP,
        'mul_literal': operators.MULTIPLY_OP,
        'div_literal': operators.DIVIDE_OP,
        'pow_literal': NotImplemented,
        'lt_literal': operators.LESS_OP,
        'le_literal': operators.LESS_EQUAL_OP,
        'ge_literal': operators.GREATER_EQUAL_OP,
        'gt_literal': operators.GREATER_OP,
        'eq_literal': operators.EQUAL_OP,
        'ne_literal': operators.NOT_EQUAL_OP,
    }

    def _visit_operator_literal(self, node, children):
        return self._operator_literal_map[node.expr_name]

    visit_add_literal = visit_sub_literal = _visit_operator_literal
    visit_mul_literal = visit_div_literal = _visit_operator_literal
    visit_pow_literal = _visit_operator_literal

    visit_lt_literal = visit_le_literal = _visit_operator_literal
    visit_ge_literal = visit_gt_literal = _visit_operator_literal
    visit_eq_literal = visit_ne_literal = _visit_operator_literal

    visit_number = visit_variable = _lift_middle
    visit_number_regex = visit_variable_regex = _lift_text
    visit__ = _lift_dontcare


_parser = None


def parse(program):
    global _parser
    if not _parser:
        _parser = _VisitorParser()
    return _parser.parse(program)
