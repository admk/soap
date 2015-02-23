from soap import logger
from soap.common import base_dispatcher
from soap.expression import is_variable, is_expression
from soap.program.flow import _indent
from soap.program.generator.flow import CodeGenerator
from soap.semantics import (
    ErrorSemantics, FloatInterval, IntegerInterval, Label, label
)


def _bound_type(bound):
    if isinstance(bound, IntegerInterval):
        return 'int'
    if isinstance(bound, ErrorSemantics):
        return 'float'
    if bound == 'input':
        return bound
    if isinstance(bound, FloatInterval):
        logger.error('Why is bound type FloatInterval?')
        return 'float'
    raise TypeError('Unrecognized bound type {}'.format(repr(bound)))


class _DeclCodeGenerator(CodeGenerator):
    def add_declaration(self, var, expr):
        raise NotImplementedError

    def _with_infix(self, expr, var_infix, label_infix='__magic__'):
        var = super()._with_infix(expr, var_infix, label_infix)
        self.add_declaration(var, expr)
        return var


def _decl_code_gen(meta_state, state, out_vars):
    decl = {}

    class Generator(_DeclCodeGenerator):
        def add_declaration(self, var, expr):
            if isinstance(expr, Label):
                bound = expr.bound
            elif is_variable(expr):
                label = self.env.get(expr)
                if label is None or is_expression(label):
                    # input variable
                    bound = 'input'
                else:
                    bound = label.bound
            else:
                return

            var = var.name
            var_type = _bound_type(bound)
            ori_type = decl.get(var)
            if ori_type and ori_type != var_type:
                if var_type == 'input':
                    return
                if ori_type != 'input':
                    logger.warning(
                        'Type collision for {}, types {} and {}, defaults to '
                        'float'.format(var, ori_type, var_type))
                    var_type = 'float'
            decl[var] = var_type

    _, env = label(meta_state, state, out_vars)
    generator = Generator(env=env, out_vars=out_vars)
    code = generator.generate()
    int_set = set()
    float_set = set()
    for k, v in decl.items():
        if v == 'input':
            v = _bound_type(state[k])
        if v == 'int':
            int_set.add(k)
        elif v == 'float':
            float_set.add(k)
        else:
            raise TypeError('Unrecognized type {}'.format(v))
    return code, int_set, float_set


class CTranspiler(base_dispatcher('transpile')):
    def generic_transpile(self, flow):
        raise TypeError('Unrecognized flow type {}'.format(type(flow)))

    _empty = lambda flow: ''

    transpile_IdentityFlow = _empty
    transpile_InputFlow = transpile_OutputFlow = _empty

    def transpile_AssignFlow(self, flow):
        return '{} = {};\n'.format(flow.var, flow.expr)

    def transpile_IfFlow(self, flow):
        true_branch = self(flow.true_flow)
        false_branch = self(flow.false_flow)
        code = 'if ({}) {{\n{}}}\n'.format(
            flow.conditional_expr, _indent(true_branch))
        if false_branch:
            code += ' else {{\n{}}}\n'.format(_indent(false_branch))
        return code

    def transpile_WhileFlow(self, flow):
        loop = self(flow.loop_flow)
        code = 'while ({}) {{\n{}}}\n'.format(
            flow.conditional_expr, _indent(loop))
        return code

    def transpile_CompositionalFlow(self, flow):
        return ''.join(self(f) for f in flow.flows)


def _generate(meta_state, state, out_vars):
    code, int_set, float_set = _decl_code_gen(meta_state, state, out_vars)
    code = CTranspiler()(code)
    return code, int_set, float_set


def _generate_declarations(int_set, float_set):
    decl = 'int {};\n'.format(', '.join(sorted(int_set)))
    decl += 'float {};\n'.format(', '.join(sorted(float_set)))
    return decl


def generate(meta_state, state, out_vars):
    code, int_set, float_set = _generate(meta_state, state, out_vars)
    decl = _generate_declarations(int_set, float_set)
    return decl + code


def generate_function(meta_state, state, out_vars, func_name):
    code, int_set, float_set = _generate(meta_state, state, out_vars)

    out_type = 'float'
    code = code + 'return {};\n'.format(
        ' && '.join(v.name + '< 0' for v in out_vars))

    inputs = {v.name for v in state}
    int_set -= inputs
    float_set -= inputs

    decl = _indent(_generate_declarations(int_set, float_set))

    inputs = ', '.join(
        '{} {}'.format(_bound_type(v), k) for k, v in state.items())
    formatter = '{out_type} {func_name}({inputs}) {{\n{decl}{code}}}\n'
    func_code = formatter.format(
        out_type=out_type, func_name=func_name, inputs=inputs,
        decl=decl, code=_indent(code))
    return func_code
