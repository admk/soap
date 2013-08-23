"""
.. module:: soap.program.parser
    :synopsis: Parser for programs.
"""
import ast

from soap.expr.parser import raise_parser_error, ast_to_expr


class Block(object):
    """A control/data flow block of a program."""
    def transition(state):
        """The statement block takes as its input a state and makes a
        transition into a new state. Each subclass should implement this member
        function."""
        raise NotImplementedError


class AssignBlock(Block):
    """Assign block."""
    def __init__(self, var, expr, next_block):
        self.var = var
        self.expr = expr
        self.next_block = next_block

    def transition(state):
        return state


class ConditionalBlock(Block):
    """Conditional block."""
    def __init__(self, expr, true_block, false_block):
        self.expr = expr
        self.true_block = true_block
        self.false_block = false_block

    def transition(state):
        return state


def ast_to_block(prog_ast, prog_str):
    for stmt in prog_ast:
        if isinstance(stmt, ast.Assign):
            pass
        elif isinstance(stmt, ast.If):
            pass
        elif isinstance(stmt, ast.While):
            pass
        else:
            raise_parser_error('Unknown statement', prog_str, stmt)


def parse(prog_str):
    ast_to_block(ast.parse(prog_str).body)

