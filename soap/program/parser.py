"""
.. module:: soap.program.parser
    :synopsis: Parser for programs.
"""
import ast

from soap.expr.parser import ast_to_expr, raise_parser_error
from soap.program.flow import (
    IdentityFlow, AssignFlow, CompositionalFlow, IfFlow, WhileFlow
)


def ast_to_flow(prog_ast, prog_str):
    """Converts abstract syntax trees into program flow :class:`Flow`
    instances."""
    flow = CompositionalFlow()
    for stmt in prog_ast:
        if isinstance(stmt, ast.Assign):
            flow += AssignFlow(
                stmt.targets.pop().id,
                ast_to_expr(stmt.value, prog_str))
        elif isinstance(stmt, ast.If):
            flow += IfFlow(
                ast_to_expr(stmt.test, prog_str),
                ast_to_flow(stmt.body, prog_str),
                ast_to_flow(stmt.orelse, prog_str))
        elif isinstance(stmt, ast.While):
            flow += WhileFlow(
                ast_to_expr(stmt.test, prog_str),
                ast_to_flow(stmt.body, prog_str))
        elif isinstance(stmt, ast.Pass):
            flow += IdentityFlow()
        else:
            raise_parser_error('Unknown statement', prog_str, stmt)
    return flow


def parse(prog_str):
    return ast_to_flow(ast.parse(prog_str).body, prog_str)
