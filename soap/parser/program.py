from soap.datatype import function_type
from soap.expression import Variable
from soap.program import FunctionFlow
from soap.parser.common import (
    _lift_child, _lift_dontcare, _lift_second, CommonVisitor
)
from soap.parser.expression import DeclarationVisitor, ExpressionVisitor
from soap.parser.grammar import compiled_grammars
from soap.parser.statement import StatementVisitor


class ProgramVisitor(object):
    visit_program = _lift_child

    def visit_function(self, node, children):
        (def_lit, new_variable, left_paren,
         input_list, right_paren, code_block) = children
        func = Variable(new_variable.name, function_type)
        return FunctionFlow(func, input_list, code_block)

    def visit_input_list(self, node, children):
        input_expr, maybe_input_list = children
        input_list = input_expr
        if maybe_input_list:
            input_list += maybe_input_list
        return input_list

    visit_maybe_input_list = _lift_child
    visit_comma_input_list = _lift_second

    def visit_input_expr(self, node, children):
        variable, colon, number = children
        return [(variable, number)]

    visit_def = _lift_dontcare


class _ProgramVisitor(
        CommonVisitor, DeclarationVisitor, ExpressionVisitor,
        StatementVisitor, ProgramVisitor):
    grammar = compiled_grammars['program']


def parse(program, decl=None):
    decl = decl or {}
    visitor = _ProgramVisitor(decl)
    return visitor.parse(program)
