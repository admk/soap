import time

from soap.analysis import analyze, Plot
from soap.context import context
from soap.expression import is_expression
from soap.parser import parse as _parse
from soap.semantics import flow_to_meta_state, luts
from soap.transformer import (
    closure, expand, parsings, reduce, greedy, frontier, thick
)
from soap.transformer.discover import unroll


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


def simulate_error(program):
    program, state, _ = parse(program)


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


def optimize(program, file_name=None):
    program, state, out_vars = parse(program)
    if not is_expression(program):
        program = flow_to_meta_state(program)
    func = _algorithm_map[context.algorithm]

    unrolled = unroll(program)
    original = analyze([unrolled], state, out_vars).pop()

    start_time = time.time()
    expr_set = func(program, state, out_vars)
    elapsed_time = time.time() - start_time

    results = analyze(expr_set, state, out_vars)
    emir = {
        'original': original,
        'inputs': state,
        'outputs': out_vars,
        'results': results,
        'time': elapsed_time,
        'context': context,
        'file': file_name,
    }
    return emir


def plot(emir, file_name):
    plot = Plot(legend_time=True)
    plot.add([emir['original']], marker='o', legend='Original')
    plot.add(emir['results'], legend='Discovered', time=emir['time'])
    plot.save('{}.pdf'.format(file_name))
    plot.show()
