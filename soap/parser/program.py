import re

import sh

from soap.datatype import type_cast
from soap.expression import is_variable
from soap.program import ProgramFlow, PragmaInputFlow, PragmaOutputFlow
from soap.parser.common import _lift_child, _lift_dontcare, CommonVisitor
from soap.parser.expression import DeclarationVisitor, ExpressionVisitor
from soap.parser.grammar import compiled_grammars
from soap.parser.statement import StatementVisitor


class PragmaVisitor(object):
    def _visit_comma_seperated_list(self, node, children):
        item, comma_item_list = children
        return [item] + [each for _, each in comma_item_list]

    def visit_pragma_input_statement(self, node, children):
        pragma_lit, input_lit, input_list = children
        return PragmaInputFlow(input_list)

    def visit_pragma_output_statement(self, node, children):
        pragma_lit, output_lit, output_list = children
        return PragmaOutputFlow(output_list)

    def visit_input_assign_expr(self, node, children):
        variable, _, number = children
        return variable, number

    def visit_input_expr(self, node, children):
        child = _lift_child(self, node, children)
        if not is_variable(child):
            return child
        return child, type_cast(child.dtype, top=True)

    visit_input_list = visit_output_list = _visit_comma_seperated_list
    visit_input = visit_output = visit_pragma = _lift_dontcare


class _ProgramVisitor(
        CommonVisitor, DeclarationVisitor, ExpressionVisitor,
        StatementVisitor, PragmaVisitor):
    grammar = compiled_grammars['statement']


def _preprocess(text):
    text = re.sub(r'#\s*pragma', '__pragma', text)
    text = sh.cpp('-E', '-P', _in=text).stdout.decode('utf-8')
    text = re.sub(r'__pragma', '#pragma', text)
    return text


def parse(program, decl=None):
    decl = decl or {}
    visitor = _ProgramVisitor(decl)
    program = _preprocess(program)
    flow = visitor.parse(program)
    return ProgramFlow(flow)
