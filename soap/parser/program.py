from os import path

from parsimonious import Grammar, nodes

from soap.expression import expression_factory, operators
from soap.program import (
    IdentityFlow, AssignFlow, IfFlow, WhileFlow, CompositionalFlow
)
from soap.semantics import cast


class _VisitorParser(nodes.NodeVisitor):
    grammar_file = path.join(path.dirname(__file__), 'program.grammar')

    def __init__(self):
        super().__init__()
        with open(self.grammar_file, 'r') as file:
            self.grammar = Grammar(file.read())

    _lift_child = nodes.NodeVisitor.lift_child
    _lift_first = lambda self, node, children: children[0]
    _lift_children = lambda self, node, children: children
    _lift_text = lambda self, node, children: node.text
    _lift_dontcare = lambda self, node, children: None

    def _lift_middle(self, node, children):
        _1, value, _2 = children
        return value

    def generic_visit(self, node, children):
        if not node.expr_name:
            return
        raise TypeError('Do not recognize node {!r}'.format(node))

    visit_statement = visit_single_statement = _lift_child

    def visit_compound_statement(self, node, children):
        single_statement, statement = children
        if not statement:
            return single_statement
        if isinstance(statement, CompositionalFlow):
            flows = list(statement.flows)
        else:
            flows = [statement]
        flows = [single_statement] + flows
        return CompositionalFlow(flows)

    def visit_skip_statement(self, node, children):
        return IdentityFlow()

    def visit_assign_statement(self, node, children):
        var, assign, expr, semicolon = children
        return AssignFlow(var, expr)

    visit_if_statement = _lift_first
    visit_if_block = _lift_child

    def visit_if_then_block(self, node, children):
        if_lit, bool_expr, true_flow = children
        return IfFlow(bool_expr, true_flow, IdentityFlow())

    def visit_if_else_block(self, node, children):
        if_flow, false_flow = children
        bool_expr = if_flow.conditional_expr
        true_flow = if_flow.true_flow
        return IfFlow(bool_expr, true_flow, false_flow)

    def visit_while_statement(self, node, children):
        while_lit, bool_expr, loop_flow, semicolon = children
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

    visit_arithmetic_expression = _lift_child

    def visit_select(self, node, children):
        bool_expr, q_lit, true_expr, c_lit, false_expr = children
        return expression_factory(
            operators.TERNARY_SELECT_OP, bool_expr, true_expr, false_expr)

    visit_term = visit_factor = _visit_concat_expr
    visit_atom = _lift_child
    visit_parened = _lift_middle

    def visit_unary_expr(self, node, children):
        op, atom = children
        if op == operators.SUBTRACT_OP:
            op = operators.UNARY_SUBTRACT_OP
        return expression_factory(op, atom)

    def _visit_maybe_list(self, node, children):
        expr_list = self._lift_child(node, children)
        if expr_list is None:
            return []
        return expr_list

    def _visit_list(self, node, children):
        expr, expr_list = children
        return [expr] + expr_list

    visit_maybe_sum_list = visit_maybe_prod_list = _visit_maybe_list
    visit_sum_list = visit_prod_list = _visit_list
    visit_sum_expr = visit_prod_expr = _lift_children

    visit_skip = visit_assign = visit_if = visit_while = _lift_dontcare
    visit_left_paren = visit_right_paren = visit_semicolon = _lift_dontcare
    visit_question = visit_colon = _lift_dontcare

    visit_boolean_operator = _lift_child

    _operator_map = {
        'add': operators.ADD_OP,
        'sub': operators.SUBTRACT_OP,
        'mul': operators.MULTIPLY_OP,
        'div': operators.DIVIDE_OP,
        'pow': NotImplemented,
        'lt': operators.LESS_OP,
        'le': operators.LESS_EQUAL_OP,
        'ge': operators.GREATER_EQUAL_OP,
        'gt': operators.GREATER_OP,
        'eq': operators.EQUAL_OP,
        'ne': operators.NOT_EQUAL_OP,
    }

    def _visit_operator(self, node, children):
        return self._operator_map[node.expr_name]

    visit_lt = visit_le = visit_ge = visit_gt = _visit_operator
    visit_eq = visit_ne = _visit_operator

    visit_sum_operator = visit_prod_operator = _lift_child

    visit_add = visit_sub = visit_mul = visit_div = visit_pow = _visit_operator

    def visit_variable(self, node, children):
        name = self._lift_middle(node, children)
        return expression_factory(name)

    def _visit_number_regex(self, node, children):
        return cast(node.text)

    visit_integer_regex = visit_float_regex = _visit_number_regex

    visit_number = _lift_middle
    visit_number_regex = _lift_child
    visit_variable_regex = _lift_text
    visit__ = _lift_dontcare

    def parse(self, program):
        tree = self.grammar.parse(program)
        return self.visit(tree)


_parser = None


def parse(program):
    global _parser
    if not _parser:
        _parser = _VisitorParser()
    return _parser.parse(program)
