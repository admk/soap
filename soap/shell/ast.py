import ast
import builtins
import inspect
import pickle

import codegen


def __cast(v):
    from soap.semantics import cast
    try:
        return cast(v)
    except Exception:
        return v
builtins.__cast = __cast


def __print(v, n):
    from soap import logger
    with logger.debug_context():
        logger.debug('{} := {!r}'.format(n, v))
    return v
builtins.__print = __print


def _local_variables():
    return list(inspect.stack())[-1][0].f_locals


def __flow(flow, vars):
    from soap import logger
    flow, vars = pickle.loads(flow), pickle.loads(vars)
    locs = _local_variables()
    new_vars = flow.flow(vars)
    debug_str = flow.format(new_vars)
    # update changes to input variables
    for k in vars:
        if not k.annotation.is_bottom():
            continue
        k = k.variable.name
        locs[k] = new_vars[k]
    # add newly added variables
    for k in new_vars:
        if k in vars:
            continue
        if not k.annotation.is_bottom():
            continue
        k = k.variable.name
        locs[k] = new_vars[k]
    logger.info('-' * 75)
    with logger.local_context(color=False):
        logger.info(debug_str)
builtins.__flow = __flow


class IPythonNodeTransformer(ast.NodeTransformer):
    def __init__(self, shell):
        self.shell = shell

    def visit(self, node):
        try:
            return super().visit(node)
        except Exception:
            self.shell.showtraceback()


class TraceExprTransformer(IPythonNodeTransformer):
    def __init__(self, shell):
        super().__init__(shell)
        for k, v in vars(ast).items():
            try:
                if issubclass(v, ast.expr):
                    setattr(self, 'visit_' + k, getattr(
                            self, 'visit_' + k, self.visit_expr))
            except TypeError:
                pass

    def visit_expr(self, node):
        if isinstance(getattr(node, 'ctx', None), ast.Store):
            return node
        if isinstance(node, (ast.Num, ast.Str)):
            return node
        source_node = ast.Str(codegen.to_source(node))
        return ast.copy_location(ast.Call(
            func=ast.Name(id='__print', ctx=ast.Load()),
            args=[self.generic_visit(node), source_node],
            keywords=[]), node)


class TraceTransformer(IPythonNodeTransformer):
    def __init__(self, shell):
        super().__init__(shell)
        self.trace_expr_transformer = TraceExprTransformer(shell)

    def visit_Call(self, node):
        if not isinstance(node.func, ast.Name):
            return node
        elif node.func.id != 'trace':
            call_node = ast.Call(
                func=node.func,
                args=[self.generic_visit(a) for a in node.args],
                keywords=[self.generic_visit(k) for k in node.keywords])
            return ast.copy_location(call_node, node)
        return self.trace_expr_transformer.visit(node.args[0])

    def visit_With(self, node):
        try:
            if node.items[0].context_expr.id == 'trace':
                return [self.trace_expr_transformer.visit(b)
                        for b in node.body]
        except AttributeError:
            pass
        with_node = ast.With(
            body=[self.generic_visit(b) for b in node.body],
            items=[self.generic_visit(i) for i in node.items])
        return ast.copy_location(with_node, node)


class CastTransformer(IPythonNodeTransformer):
    def visit_List(self, node):
        return ast.copy_location(ast.Call(
            func=ast.Name(id='__cast', ctx=ast.Load()),
            args=[self.generic_visit(node)], keywords=[]), node)


class FlowTransformer(IPythonNodeTransformer):
    class VariableVisitor(ast.NodeVisitor):
        def __init__(self, magics_only=True):
            self.magics_only = magics_only
            self.vars = {}
            self.locals = _local_variables()

        def visit_Name(self, node):
            from soap.semantics import Interval, ErrorSemantics
            v = self.locals.get(node.id, None)
            if self.magics_only:
                if not isinstance(v, (Interval, ErrorSemantics)):
                    return
            if v is None:
                v = Interval(bottom=True)
            self.locals[node.id] = v

        def visit(self, node):
            super().visit(node)
            return self.vars

    def _transform_node_to_flow(self, node):
        from soap.program.parser import ast_to_flow
        from soap.semantics import IdentifierBoxState
        vars = {}
        for n in node:
            vars.update(self.VariableVisitor(magics_only=False).visit(n))
        return ast.parse('__flow({!r}, {!r})'.format(
            pickle.dumps(ast_to_flow(node, self.shell.raw_cell)),
            pickle.dumps(IdentifierBoxState(vars)))).body[0]

    def visit_control_structure(self, node):
        # collect variables in conditions
        cond_vars = self.VariableVisitor(magics_only=True).visit(node.test)
        # no magics in condition, usual python execution
        if not cond_vars:
            return node
        # magical stuff in condition, execute with soap.program.flow
        return ast.copy_location(self._transform_node_to_flow([node]), node)

    def visit_If(self, node):
        return self.visit_control_structure(node)

    def visit_While(self, node):
        return self.visit_control_structure(node)

    def visit_With(self, node):
        try:
            name = node.items[0].context_expr.id
        except AttributeError:
            name = None
        if name == 'flow':
            flow_node = self._transform_node_to_flow(node.body)
            return ast.copy_location(flow_node, node)
        with_node = ast.With(
            body=[self.generic_visit(b) for b in node.body],
            items=[self.generic_visit(i) for i in node.items])
        return ast.copy_location(with_node, node)


builtins.__flow_dict = {}


def trace(_):
    return _
