from parsimonious import nodes

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


class ParserError(Exception):
    pass


class CommonVisitor(nodes.NodeVisitor):
    def generic_visit(self, node, children):
        if not node.expr_name:
            return children
        raise TypeError('Do not recognize node {!r}'.format(node))

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

    visit_left_brac = visit_right_brac = visit_comma = _lift_dontcare
    visit_left_paren = visit_right_paren = visit_semicolon = _lift_dontcare
    visit_left_curl = visit_right_curl = _lift_dontcare
    visit_question = visit_colon = _lift_dontcare

    def _visit_number_regex(self, node, children):
        text = node.text
        if text.endswith('f'):
            text = text[:-1]
        return cast(text)

    visit_integer_regex = visit_real_regex = _visit_number_regex

    visit_integer = visit_real = _lift_middle
    visit_variable_regex = _lift_text

    visit__no_new_line = visit__ = _lift_dontcare
