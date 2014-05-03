import copy

from soap.expression import is_variable, is_expression, StateGetterExpr
from soap.label import Label
from soap.program.flow import AssignFlow, CompositionalFlow
from soap.semantics import is_numeral


def _dependency_dictionary(env, vars):
    """
    Extract dependencies from env.

    Example::
        [x -> j + k, y -> l + k, k -> j + h]

    Produces::
        deps == {x: {j, k}, y: {l, k}, h: set(), j: set(), k: {j, h}, l: set()}
    """
    deps = {}
    for var in vars:
        expr = env.get(var)

        # find dependent variables for the corresponding expression
        if not expr:
            # can't find expression for var or var is an input variable, so
            # there are no dependencies for it
            expr_deps = set()
        elif isinstance(expr, StateGetterExpr):
            raise NotImplementedError(
                'TODO special treatment for this, because of the labelling '
                'behaviour.')
        elif is_expression(expr):
            # dependent variables in the expression
            expr_deps = expr.vars()
        elif isinstance(expr, Label):
            # is a label, dependency is itself
            expr_deps = {expr}
        elif is_variable(expr):
            # is an input variable, technically not really a dependency
            expr_deps = set()
        elif is_numeral(expr):
            # is constant value, no dependent inputs
            expr_deps = set()
        else:
            raise TypeError(
                'Do not know how to find dependencies in expression {!r}'
                .format(expr))

        # set the list of dependent variables
        deps[var] = expr_deps

        # finds the dependencies of dependent variables
        dep_deps = _dependency_dictionary(env, expr_deps)

        # merge update dep_deps into deps
        for each_var in set(deps) | set(dep_deps):
            each_deps = deps.setdefault(each_var, set())
            each_deps |= dep_deps.get(each_var, set())

    return deps


def _dependency_order(deps):
    """
    Recursively (iteratively) pop variables with resolved dependencies from
    dependency dictionary for code synthesis, until deps is empty

    Example::
        # {x: {j, k}, y: {l, k}, h: set(), j: set(), k: {j, h}, l: set()}
        yield {h, j, l}
        # {x: {k}, y: {k}, k: set()}
        yield {k}
        # {x: set(), y: set()}
        yield {x, y}
    """
    deps = copy.deepcopy(deps)
    # find independent variables
    indeps = set()
    for var, dep in deps.items():
        if dep:
            continue
        indeps.add(var)
    yield indeps
    # remove refences of [variables in indeps] in deps, and repeat
    for var in indeps:
        del deps[var]
        for op_var, op_dep in deps.items():
            deps[op_var] = op_dep - {var}

    # find next variables with resolved dependencies
    if deps:
        yield from _dependency_order(deps)


def dependency_order(env, vars):
    yield from _dependency_order(_dependency_dictionary(env, vars))


class _Generator(object):
    def generate(self, env, vars):
        deps = dependency_order(env, vars)
        flows = []
        for vars in deps:
            for var in vars:
                expr = env[var]
                method = getattr(
                    self, 'generate_' + expr.__class__.__name__,
                    self.generic_generate)
                flow = method(var, expr)
                if isinstance(flow, CompositionalFlow):
                    flows += flow.flows
                else:
                    flows.append(flow)
        return CompositionalFlow(flows)

    def generic_generate(self, var, expr):
        return AssignFlow(var, expr)


def generate(env, vars):
    return _Generator().generate(env, vars)
