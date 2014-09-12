from soap.analysis import analyze, Plot
from soap.context import context
from soap.expression import is_expression
from soap.parser import parse as _parse
from soap.semantics import flow_to_meta_state, luts
from soap.transformer import (
    closure, expand, parsings, reduce, greedy, frontier, thick
)


def parse(program):
    if isinstance(program, str):
        if program.endswith('.soap'):
            with open(program) as file:
                program = file.read()
        program = _parse(program)
    state = program.inputs()
    out_vars = program.outputs()
    return program, state, out_vars


def analyze_error(program):
    program, state, _ = parse(program)
    return program.debug(state)


def analyze_resource(program):
    program, state, out_vars = parse(program)
    return luts(flow_to_meta_state(program), state, out_vars)


_algorithm_map = {
    'closure': lambda s, _1, _2: closure(s),
    'expand': lambda s, _1, _2: expand(s),
    'parsings': lambda s, _1, _2: parsings(s),
    'reduce': lambda s, _1, _2: reduce(s),
    'greedy': greedy,
    'frontier': frontier,
    'thick': thick,
}


def optimize(program):
    program, state, out_vars = parse(program)
    if not is_expression(program):
        program = flow_to_meta_state(program)
    func = _algorithm_map[context.algorithm]
    expr_set = func(program, state, out_vars)
    return analyze(expr_set, state, out_vars)


def plot(emir, file_name):
    plot = Plot(legend_time=True)
    plot.add(emir)
    plot.save('{}.pdf'.format(file_name))
    plot.show()
