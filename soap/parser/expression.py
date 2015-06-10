from soap.datatype import (
    auto_type, int_type, real_type, IntegerArrayType, RealArrayType
)
from soap.expression import expression_factory, operators, Variable
from soap.parser.common import (
    ParserError, _lift_child, _lift_children, _lift_middle, _lift_second,
    _visit_list, _visit_maybe_list, CommonVisitor
)
from soap.parser.grammar import compiled_grammars


def _visit_concat_expr(self, node, children):
    expr, expr_list = children
    for each_expr in expr_list:
        each_op, each_factor = each_expr
        expr = expression_factory(each_op, expr, each_factor)
    return expr


class VariableNotDeclaredError(ParserError):
    """Variable was not declared.  """


class VariableAlreadyDeclaredError(ParserError):
    """Variable was already declared.  """


class ArrayDimensionError(ParserError):
    """Array dimension mismatch.  """


class DeclarationVisitor(object):
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


class UntypedDeclarationVisitor(DeclarationVisitor):
    def visit_variable(self, node, children):
        var = self.visit_new_variable(node, children)
        if not var.dtype:
            return Variable(var.name, auto_type)
        return var


class ExpressionVisitor(object):
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

    visit_unary_subtract = visit_unary_expr

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
        'exp': operators.EXPONENTIATE_OP,
        'sin': NotImplemented,
        'cos': NotImplemented,
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
    visit_unary_operator = _lift_child

    visit_add = visit_sub = visit_mul = visit_div = visit_pow = _visit_operator
    visit_exp = visit_sin = visit_cos = _visit_operator


class _UntypedExpressionVisitor(
        CommonVisitor, UntypedDeclarationVisitor, ExpressionVisitor):
    grammar = compiled_grammars['expression']


def expr_parse(expression, decl=None):
    # FIXME temporary hack for broken parser
    expression = '({})'.format(expression)
    decl = decl or {}
    visitor = _UntypedExpressionVisitor(decl)
    return visitor.parse(expression)
