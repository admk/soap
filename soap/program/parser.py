"""
.. module:: soap.program.parser
    :synopsis: Parser for programs.
"""
import ast

from soap.expr.parser import ast_to_expr, raise_parser_error
from soap.expr import Expr

from soap.program.flow import AssignFlow, IfFlow, WhileFlow, CompositionalFlow


def ast_to_flow(prog_ast, prog_str):
    """Converts abstract syntax trees into program flow :class:`Flow`
    instances."""
    def ast_to_arithexpr(expr):
        return ast_to_expr(expr, Expr, prog_str)

    def ast_to_boolexpr(expr):
        return ast_to_expr(expr, Expr, prog_str)

    flow = CompositionalFlow()
    for stmt in prog_ast:
        if isinstance(stmt, ast.Assign):
            flow += AssignFlow(
                stmt.targets.pop().id,
                ast_to_arithexpr(stmt.value))
        elif isinstance(stmt, ast.If):
            flow += IfFlow(
                ast_to_boolexpr(stmt.test),
                ast_to_flow(stmt.body, prog_str),
                ast_to_flow(stmt.orelse, prog_str))
        elif isinstance(stmt, ast.While):
            flow += WhileFlow(
                ast_to_boolexpr(stmt.test),
                ast_to_flow(stmt.body, prog_str))
        else:
            raise_parser_error('Unknown statement', prog_str, stmt)
    return flow


def parse(prog_str):
    return ast_to_flow(ast.parse(prog_str).body, prog_str)


if __name__ == '__main__':
    print(parse("""while x > 1: x = 0.9 * x"""))
