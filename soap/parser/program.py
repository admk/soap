from soap.datatype import type_cast
from soap.expression import is_variable
from soap.program import ProgramFlow, PragmaInputFlow, PragmaOutputFlow
from soap.parser.common import (
    _lift_child, _lift_dontcare, _lift_second, _visit_maybe_list, _visit_list,
    CommonVisitor
)
from soap.parser.expression import DeclarationVisitor, ExpressionVisitor
from soap.parser.grammar import compiled_grammars
from soap.parser.statement import StatementVisitor


class PragmaVisitor(object):
    def visit_pragma_input_statement(self, node, children):
        pragma_lit, input_lit, input_list, _ = children
        return PragmaInputFlow(input_list)

    def visit_input_list(self, node, children):
        input_expr, maybe_input_list = children
        input_list = input_expr
        if maybe_input_list:
            input_list += maybe_input_list
        return input_list

    visit_maybe_input_list = _lift_child
    visit_comma_input_list = _lift_second

    def visit_input_expr(self, node, children):
        child = _lift_child(self, node, children)
        if is_variable(child):
            top = type_cast(child.dtype, top=True)
            child = (child, top)
        return [child]

    def visit_input_assign_expr(self, node, children):
        variable, colon, number = children
        return variable, number

    def visit_pragma_output_statement(self, node, children):
        pragma_lit, output_lit, output_list, _ = children
        return PragmaOutputFlow(output_list)

    visit_output_list = _visit_list
    visit_maybe_output_list = _visit_maybe_list
    visit_comma_output_list = _lift_second

    visit_input = visit_output = visit_pragma = _lift_dontcare


class _ProgramVisitor(
        CommonVisitor, DeclarationVisitor, ExpressionVisitor,
        StatementVisitor, PragmaVisitor):
    grammar = compiled_grammars['statement']


def _preprocess(text):
    text = text.split('\n')
    new_text = []
    line_cont = False
    for line in text:
        if line_cont:
            line = new_text.pop() + line
        if line.rstrip().endswith('\\'):
            line_cont = True
            line = line.rstrip()[:-1] + ' '
        new_text.append(line)
    return '\n'.join(new_text)


def parse(program, decl=None):
    decl = decl or {}
    visitor = _ProgramVisitor(decl)
    program = _preprocess(program)
    return ProgramFlow(visitor.parse(program))
