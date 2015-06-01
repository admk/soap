import random
import time

from soap import logger
from soap.analysis import frontier as analysis_frontier, Plot
from soap.context import context
from soap.expression import is_expression
from soap.parser import parse as _parse
from soap.semantics import (
    arith_eval, BoxState, ErrorSemantics, flow_to_meta_state, MetaState,
    IntegerInterval
)
from soap.semantics.schedule.table import s
from soap.transformer import (
    closure, expand, frontier, greedy, parsings, reduce, thick
)


def parse(program):
    if isinstance(program, str):
        if program.endswith('.soap'):
            with open(program) as file:
                program = file.read()
        program = _parse(program)
    state = BoxState(program.inputs)
    out_vars = program.outputs
    return program, state, out_vars


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
        logger.unpersistent('Sim')
    except KeyboardInterrupt:
        pass
    return max_error


def simulate_error(program, population_size):
    program, state, out_vars = parse(program)
    samples = _generate_samples(state, population_size)
    return _run_simulation(flow_to_meta_state(program), samples, out_vars)


_algorithm_map = {
    'closure': lambda expr_set, _1, _2: closure(expr_set),
    'expand': lambda expr_set, _1, _2: expand(expr_set),
    'parsings': lambda expr_set, _1, _2: parsings(expr_set),
    'reduce': lambda expr_set, _1, _2: reduce(expr_set),
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

    original = analysis_frontier([program], state, out_vars).pop()

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


def plot(emir, file_name, reanalyze=False):
    plot = Plot()
    results = emir['results']
    original = emir['original']
    func_name = emir['context'].algorithm
    plot.add_original(original)
    plot.add(results, legend='{} ({:.2f}s)'.format(func_name, emir['time']))
    plot.save('{}.pdf'.format(emir['file']))
    plot.show()


def report(emir, file_name):
    def sub_report(result):
        samples = _generate_samples(emir['inputs'], 100)
        sim_error = _run_simulation(
            result.expression, samples, emir['outputs'])
        return {
            'Accuracy': {
                'Error Bound': float(result.error),
                'Simulation': float(sim_error),
            },
            'Resources': {
                'Estimated': {
                    'LUTs': result.lut,
                    'Registers': result.ff,
                    'DSP Elements': result.dsp,
                },
            },
        }
    original = emir['original']
    results = sorted(emir['results'])
    report = {
        'Name': file_name,
        'Time': emir['time'],
        'Total': len(emir['results']),
        'Statistics': {
            'Original': sub_report(original),
            'Fewest Resources': sub_report(results[0]),
            'Most Accurate': sub_report(results[-1]),
            'Best Latency': sub_report(...),
        },
        'Context': emir['context'],
    }
    return report
