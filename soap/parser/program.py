from parsimonious import nodes

from soap.expression import expression_factory, operators, Variable
from soap.datatype import (
    auto_type, int_type, real_type, IntegerArrayType, RealArrayType
)
from soap.program import (
    IdentityFlow, AssignFlow, IfFlow, WhileFlow, CompositionalFlow,
    InputFlow, OutputFlow,
)
from soap.parser.grammar import expression_grammar, program_grammar
from soap.semantics import cast, ErrorSemantics


_lift_child = nodes.NodeVisitor.lift_child
_lift_first = lambda self, node, children: children[0]
_lift_second = lambda self, node, children: children[1]
_lift_children = lambda self, node, children: children
_lift_text = lambda self, node, children: node.text
_lift_dontcare = lambda self, node, children: None


def _lift_middle(self, node, children):
    _1, value, _2 = children
    return value


def _visit_concat_expr(self, node, children):
    expr, expr_list = children
    for each_expr in expr_list:
        each_op, each_factor = each_expr
        expr = expression_factory(each_op, expr, each_factor)
    return expr


def _visit_maybe_list(self, node, children):
    expr_list = _lift_child(self, node, children)
    if expr_list is None:
        return []
    return expr_list


def _visit_list(self, node, children):
    expr, expr_list = children
    return [expr] + expr_list


class _CommonVisitor(nodes.NodeVisitor):
    def generic_visit(self, node, children):
        if not node.expr_name:
            return
        raise TypeError('Do not recognize node {!r}'.format(node))

    visit_integer_list = _visit_list
    visit_maybe_integer_list = _visit_maybe_list
    visit_comma_integer_list = _lift_second

    visit_variable_list = _visit_list
    visit_maybe_variable_list = _visit_maybe_list
    visit_comma_variable_list = _lift_second

    visit_expression_list = _visit_list
    visit_maybe_expression_list = _visit_maybe_list
    visit_comma_expression_list = _lift_second

    def visit_number(self, node, children):
        child = _lift_child(self, node, children)
        if isinstance(child, str):
            return cast(child)
        return child

    def visit_error(self, node, children):
        value, error = children
        if isinstance(value, ErrorSemantics):
            value = value.v
        if isinstance(error, ErrorSemantics):
            error = error.v
        return ErrorSemantics(value, error)

    def visit_interval(self, node, children):
        left_brac, min_val, comma, max_val, right_brac = children
        if isinstance(min_val, ErrorSemantics):
            min_val = min_val.v
        if isinstance(max_val, ErrorSemantics):
            max_val = max_val.v
        min_val = min_val.min
        max_val = max_val.max
        return cast([min_val, max_val])

    visit_scalar = _lift_child

    visit_skip = visit_assign = _lift_dontcare
    visit_if = visit_else = visit_while = _lift_dontcare
    visit_input = visit_output = _lift_dontcare

    visit_left_brac = visit_right_brac = visit_comma = _lift_dontcare
    visit_left_paren = visit_right_paren = visit_semicolon = _lift_dontcare
    visit_left_curl = visit_right_curl = _lift_dontcare
    visit_question = visit_colon = _lift_dontcare

    def _visit_number_regex(self, node, children):
        return cast(node.text)

    visit_integer_regex = visit_real_regex = _visit_number_regex

    visit_integer = visit_real = _lift_middle
    visit_variable_regex = _lift_text

    visit__ = _lift_dontcare


class ParserError(Exception):
    pass


class VariableNotDeclaredError(ParserError):
    """Variable was not declared.  """


class VariableAlreadyDeclaredError(ParserError):
    """Variable was already declared.  """


class ArrayDimensionError(ParserError):
    """Array dimension mismatch.  """


class _DeclarationVisitor(object):
    def __init__(self, decl=None):
        super().__init__()
        self.decl_map = decl or {}

    visit_variable_or_declaration = _lift_child

    def visit_variable_declaration(self, node, children):
        decl_type, var = children
        if var.dtype is not None or var.name in self.decl_map:
            raise VariableAlreadyDeclaredError(
                'Variable {} is already declared with type {}'
                .format(var.name, var.dtype))
        self.decl_map[var.name] = decl_type
        return Variable(var.name, decl_type)

    def visit_variable(self, node, children):
        var = self.visit_new_variable(node, children)
        if not var.dtype:
            raise VariableNotDeclaredError(
                'Variable {} is not declared'.format(var.name))
        return var

    def visit_new_variable(self, node, children):
        name = _lift_middle(self, node, children)
        dtype = self.decl_map.get(name)
        return Variable(name, dtype)

    visit_variable_subscript = _lift_child

    def visit_variable_with_subscript(self, node, children):
        var, _1, subscript, _2 = children
        dtype = var.dtype
        if dtype is not auto_type and len(dtype.shape) != len(subscript):
            raise ArrayDimensionError(
                'Variable {} is a {}-dimensional array of type {}, '
                'but subscript [{}] is {}-dimensional.'.format(
                    var, len(dtype.shape), dtype,
                    ', '.join(str(s) for s in subscript), len(subscript)))
        return expression_factory(operators.INDEX_ACCESS_OP, var, subscript)

    visit_data_type = _lift_child

    def visit_array_type(self, node, children):
        base_type, left_brac, dimension_list, right_brac = children
        if base_type == int_type:
            return IntegerArrayType(dimension_list)
        elif base_type == real_type:
            return RealArrayType(dimension_list)
        raise TypeError('Unrecognized data type {}'.format(base_type))

    visit_dimension_list = _visit_list
    visit_maybe_dimension_list = _visit_maybe_list
    visit_comma_dimension_list = _lift_second

    visit_base_type = _lift_child

    _type_map = {
        'int_type': int_type,
        'real_type': real_type,
    }

    def _visit_type(self, node, children):
        return self._type_map[node.expr_name]

    visit_int_type = visit_real_type = _visit_type


class _UntypedDeclarationVisitor(_DeclarationVisitor):
    def visit_variable(self, node, children):
        var = self.visit_new_variable(node, children)
        if not var.dtype:
            return Variable(var.name, auto_type)
        return var


class _ExpressionVisitor(object):
    visit_expression = visit_boolean_expression = _lift_child

    visit_boolean_term = visit_and_factor = _visit_concat_expr
    visit_bool_atom = _lift_child
    visit_bool_parened = _lift_middle

    visit_maybe_or_list = visit_maybe_and_list = _visit_maybe_list
    visit_or_list = visit_and_list = _visit_list
    visit_or_expr = visit_and_expr = _lift_children

    def visit_binary_bool_expr(self, node, children):
        a1, op, a2 = children
        return expression_factory(op, a1, a2)

    def visit_unary_bool_expr(self, node, children):
        op, a = children
        return expression_factory(op, a)

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

    visit_maybe_sum_list = visit_maybe_prod_list = _visit_maybe_list
    visit_sum_list = visit_prod_list = _visit_list
    visit_sum_expr = visit_prod_expr = _lift_children

    visit_compare_operator = _lift_child

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
        'and': operators.AND_OP,
        'or': operators.OR_OP,
        'not': operators.UNARY_NEGATION_OP,
    }

    def _visit_operator(self, node, children):
        return self._operator_map[node.expr_name]

    visit_lt = visit_le = visit_ge = visit_gt = _visit_operator
    visit_eq = visit_ne = _visit_operator

    visit_and = visit_or = visit_not = _visit_operator

    visit_sum_operator = visit_prod_operator = _lift_child

    visit_add = visit_sub = visit_mul = visit_div = visit_pow = _visit_operator


class _ProgramVisitor(object):
    visit_program = _lift_child

    def visit_function(self, node, children):
        (def_lit, new_variable, left_paren,
         input_list, right_paren, code_block) = children
        return FunctionFlow(new_variable, input_list, code_block)

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

    def visit_input_statement(self, node, children):
        input_lit, left_paren, input_list, right_paren, semicolon = children
        return InputFlow(input_list)

    def visit_input_list(self, node, children):
        input_expr, maybe_input_list = children
        input_list = input_expr
        if maybe_input_list:
            input_list.update(maybe_input_list)
        return input_list

    visit_maybe_input_list = _lift_child
    visit_comma_input_list = _lift_second

    def visit_input_expr(self, node, children):
        variable, colon, number = children
        return {variable: number}

    def visit_output_statement(self, node, children):
        output_lit, left_paren, output_list, right_paren, semicolon = children
        return OutputFlow(output_list)


class _Visitor(
        _CommonVisitor, _DeclarationVisitor, _ExpressionVisitor,
        _ProgramVisitor):
    grammar = program_grammar


class _UntypedExpressionVisitor(
        _CommonVisitor, _UntypedDeclarationVisitor, _ExpressionVisitor):
    grammar = expression_grammar


def parse(program, decl=None):
    decl = decl or {}
    visitor = _Visitor(decl)
    return visitor.parse(program)


def expr_parse(expression, decl=None):
    # FIXME temporary hack for broken parser
    expression = '({})'.format(expression)
    decl = decl or {}
    visitor = _UntypedExpressionVisitor(decl)
    return visitor.parse(expression)
