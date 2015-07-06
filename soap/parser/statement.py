from soap.program import (
    SkipFlow, AssignFlow, IfFlow, WhileFlow, ForFlow, CompositionalFlow
)
from soap.parser.common import (
    _lift_child, _lift_first, _lift_middle, _lift_dontcare, CommonVisitor
)
from soap.parser.expression import DeclarationVisitor, ExpressionVisitor
from soap.parser.grammar import compiled_grammars


class StatementVisitor(object):
    visit_statement = visit_single_statement = _lift_child

    def visit_compound_statement(self, node, children):
        single_statement, statement = children
        if statement is None:
            return single_statement
        if isinstance(statement, CompositionalFlow):
            flows = list(statement.flows)
        else:
            flows = [statement]
        flows = [single_statement] + flows
        return CompositionalFlow(flows)

    def visit_skip_statement(self, node, children):
        return SkipFlow()

    visit_declaration_statement = visit_skip_statement

    visit_assign_statement = _lift_first

    visit_if_statement = _lift_child

    def visit_if_then_block(self, node, children):
        if_lit, bool_expr, true_flow = children
        return IfFlow(bool_expr, true_flow, SkipFlow())

    def visit_if_else_block(self, node, children):
        if_flow, else_lit, false_flow = children
        bool_expr = if_flow.conditional_expr
        true_flow = if_flow.true_flow
        return IfFlow(bool_expr, true_flow, false_flow)

    def visit_while_statement(self, node, children):
        while_lit, bool_expr, loop_flow = children
        return WhileFlow(bool_expr, loop_flow)

    def visit_for_statement(self, node, children):
        (for_lit, left_paren, init_flow, semicolon_1, cond_expr,
         semicolon_2, incr_flow, right_paren, loop_flow) = children
        return ForFlow(init_flow, cond_expr, incr_flow, loop_flow)

    def visit_for_assign_part(self, node, children):
        child = _lift_child(self, node, children)
        if isinstance(child, AssignFlow):
            return child
        return SkipFlow()

    def visit_assign_part(self, node, children):
        var, assign, expr = children
        return AssignFlow(var, expr)

    visit_boolean_block = visit_code_block = _lift_middle

    visit_skip = visit_assign = _lift_dontcare
    visit_if = visit_else = visit_while = visit_for = _lift_dontcare
    visit_input = visit_output = visit_return = _lift_dontcare


class _StatementVisitor(
        CommonVisitor, DeclarationVisitor, ExpressionVisitor,
        StatementVisitor):
    grammar = compiled_grammars['statement']


def stmt_parse(program, decl=None):
    decl = decl or {}
    visitor = _StatementVisitor(decl)
    return visitor.parse(program)
