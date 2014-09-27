import random
import time

from soap import logger
from soap.analysis import frontier as analysis_frontier, Plot
from soap.context import context
from soap.expression import is_expression
from soap.parser import parse as _parse
from soap.semantics import (
    arith_eval, BoxState, ErrorSemantics, flow_to_meta_state, MetaState,
    IntegerInterval, luts
)
from soap.semantics.functions import error_eval, resources
from soap.transformer import (
    closure, expand, frontier, greedy, parsings, reduce, thick
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


def _generate_samples(iv, population_size):
    random.seed(0)

    def sample(error):
        if isinstance(error, IntegerInterval):
            v = random.randrange(error.min, error.max + 1)
            return IntegerInterval([v, v])
        v = random.uniform(error.v.min, error.v.max)
        e = random.uniform(error.e.min, error.e.max)
        return ErrorSemantics(v, e)

    samples = [
        BoxState({var: sample(error) for var, error in iv.items()})
        for i in range(population_size)]
    return samples


def _run_simulation(program, samples, rv):
    max_error = 0
    n = len(samples)
    try:
        for i, iv in enumerate(samples):
            logger.persistent(
                'Sim', '{}/{}'.format(i + 1, n), l=logger.levels.debug)
            result_state = arith_eval(program, iv)
            error = max(
                max(abs(error.e.min), abs(error.e.max))
                for var, error in result_state.items() if var in rv)
            max_error = max(error, max_error)
    except KeyboardInterrupt:
        pass
    return max_error


def simulate_error(program, population_size):
    program, state, out_vars = parse(program)
    samples = _generate_samples(state, population_size)
    return _run_simulation(flow_to_meta_state(program), samples, out_vars)


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
        program = MetaState({
            k: v for k, v in program.items() if k in out_vars})
    func = _algorithm_map[context.algorithm]

    unrolled = unroll(program)
    original = analysis_frontier([unrolled], state, out_vars).pop()

    start_time = time.time()
    expr_set = func(program, state, out_vars)
    elapsed_time = time.time() - start_time

    results = analysis_frontier(expr_set, state, out_vars)
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


def _reanalyze_error_estimate(result, emir):
    _, inputs, outputs = parse(emir['file'])
    meta_state = MetaState({
        k: v for k, v in result.expression.items()
        if k in outputs})
    error_min, error_max = error_eval(meta_state, inputs).e
    return float(max(abs(error_min), abs(error_max)))


def _reanalyze_resource_estimates(result, emir):
    _, inputs, outputs = parse(emir['file'])
    return resources(
        result.expression, inputs, outputs, emir['context'].precision)


def _reanalyze_results(results, emir):
    _, inputs, outputs = parse(emir['file'])
    new_results = []
    n = len(results)
    for i, r in enumerate(results):
        logger.persistent('Reanalyzing', '{}/{}'.format(i + 1, n))
        error = _reanalyze_error_estimate(r, emir)
        dsp, ff, lut = _reanalyze_resource_estimates(r, emir)
        new_results.append(r.__class__(
            lut=lut, dsp=dsp, error=error, expression=r.expression))
    return new_results


def plot(emir, file_name):
    plot = Plot(legend_time=True)
    results = _reanalyze_results(emir['results'], emir)
    original = _reanalyze_results([emir['original']], emir)
    func_name = emir['context'].algorithm.__name__
    plot.add(results, legend=func_name, time=emir['time'])
    plot.add(original, marker='o', frontier=False, legend='Original')
    plot.save('{}.pdf'.format(emir['file']))
    plot.show()


def report(emir, file_name):
    def sub_report(result):
        stats = _reanalyze_resource_estimates(result, emir)
        samples = _generate_samples(emir['inputs'], 100)
        ana_error = _reanalyze_error_estimate(result, emir)
        sim_error = _run_simulation(
            result.expression, samples, emir['outputs'])
        return {
            'Accuracy': {
                'Error Bound': float(ana_error),
                'Simulation': float(sim_error),
            },
            'Resources': {
                'LUTs': stats.lut,
                'Registers': stats.ff,
                'DSP Elements': stats.dsp,
            },
            'Performance': {
                'Fmax': None,
            },
        }
    original = emir['original']
    results = sorted(emir['results'])
    report = {
        'Name': file_name,
        'Statistics': {
            'Original': sub_report(original),
            'Fewest Resources': sub_report(results[0]),
            'Most Accurate': sub_report(results[-1]),
        },
    }
    return report
