from soap.program import (
    IdentityFlow, AssignFlow, IfFlow, WhileFlow, CompositionalFlow, ReturnFlow
)
from soap.parser.common import (
    _lift_child, _lift_middle, _lift_dontcare, CommonVisitor
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
        return IdentityFlow()

    visit_declaration_statement = visit_skip_statement

    def visit_assign_statement(self, node, children):
        var, assign, expr, semicolon = children
        return AssignFlow(var, expr)

    visit_if_statement = _lift_child

    def visit_if_then_block(self, node, children):
        if_lit, bool_expr, true_flow = children
        return IfFlow(bool_expr, true_flow, IdentityFlow())

    def visit_if_else_block(self, node, children):
        if_flow, else_lit, false_flow = children
        bool_expr = if_flow.conditional_expr
        true_flow = if_flow.true_flow
        return IfFlow(bool_expr, true_flow, false_flow)

    def visit_while_statement(self, node, children):
        while_lit, bool_expr, loop_flow = children
        return WhileFlow(bool_expr, loop_flow)

    visit_boolean_block = visit_code_block = _lift_middle

    def visit_return_statement(self, node, children):
        output_lit, output_list, semicolon = children
        return ReturnFlow(output_list)

    visit_skip = visit_assign = _lift_dontcare
    visit_if = visit_else = visit_while = _lift_dontcare
    visit_input = visit_output = visit_return = _lift_dontcare


class _StatementVisitor(
        CommonVisitor, DeclarationVisitor, ExpressionVisitor,
        StatementVisitor):
    grammar = compiled_grammars['statement']


def stmt_parse(program, decl=None):
    decl = decl or {}
    visitor = _StatementVisitor(decl)
    return visitor.parse(program)
