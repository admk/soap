import os
import random
import re
import shutil
import tempfile
import time

import sh
from akpytemp.utils import code_gobble

from soap import logger
from soap.analysis import frontier as analysis_frontier, Plot
from soap.context import context
from soap.expression import is_expression
from soap.flopoco.common import cd
from soap.parser import parse as _parse
from soap.program.generator.c import generate_function
from soap.semantics import (
    arith_eval, BoxState, ErrorSemantics, flow_to_meta_state, MetaState,
    IntegerInterval, luts
)
from soap.semantics.functions import error_eval, resources
from soap.semantics.label import s
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


def plot(emir, file_name, reanalyze=False):
    plot = Plot(legend_time=True)
    results = emir['results']
    original = [emir['original']]
    if reanalyze:
        results = _reanalyze_results(results, emir)
        original = _reanalyze_results(original, emir)
    func_name = emir['context'].algorithm
    plot.add(results, legend=func_name, time=emir['time'])
    plot.add(original, marker='o', frontier=False, legend='original')
    plot.save('{}.pdf'.format(emir['file']))
    plot.show()


def _extract(key, file):
    val = re.search(key + ': ([,\d]+)', file)
    if not val:
        return
    val = val.groups()[0]
    val = val.replace(',', '')
    return int(val)


def _get_legup_stats():
    with open('resources.legup.rpt') as f:
        file = f.read()
    dsp = _extract('DSP Elements', file)
    ff = _extract('Registers', file)
    lut = _extract('Combinational', file)
    return s(dsp, ff, lut)


def _get_quartus_stats():
    with open('func.fit.summary') as f:
        file = f.read()
    dsp = _extract('DSP block 18-bit elements ', file)
    ff = _extract('logic registers ', file)
    lut = _extract('Combinational ALUTs ', file)
    return s(dsp, ff, lut)


def _get_quartus_fmax():
    with open('func.sta.rpt') as f:
        file = f.readlines()
    for line_no, line in enumerate(file):
        if 'Slow 900mV 85C Model Fmax Summary' not in line:
            continue
        fmax_line_no = line_no + 4
        if fmax_line_no >= len(file):
            continue
        fmax_line = file[fmax_line_no]
        val = re.search('([.\d]+) MHz', fmax_line)
        if not val:
            continue
        return(float(val.groups()[0]))


def legup_and_quartus(meta_state, state, out_vars):
    def _wrap_in_main(func):
        code = code_gobble(
            """
            {}

            int main() {{
                float rv = func({});
                return 0;
            }}
            """).format(func, ', '.join('1' for _ in state))
        return code

    logger.info('Generating code...')
    code = _wrap_in_main(
        generate_function(meta_state, state, out_vars, 'func'))
    legup_path = os.path.expanduser('~/legup/examples')
    makefile = code_gobble(
        """
        NAME=test
        TOP=func
        FAMILY=StratixIV
        NO_OPT=1
        NO_INLINE=1
        LEVEL={}
        include $(LEVEL)/Makefile.common
        """).format(legup_path)
    d = tempfile.mktemp(suffix='/')
    legup_stats = quartus_stats = fmax = None
    try:
        with cd(d):
            with open('test.c', 'w') as f:
                f.write(code)
            with open('Makefile', 'w') as f:
                f.write(makefile)
            logger.info('LegUp...')
            sh.make(_out='legup.out', _err='legup.err')
            legup_stats = _get_legup_stats()
            logger.info(
                'LegUp done {}, Quartus mapping...'.format(legup_stats))
            sh.make('p')
            sh.make('q')
            logger.info('Quartus fitting & timing...')
            sh.make('f', _out='quartus.out', _err='quartus.err')
            quartus_stats = _get_quartus_stats()
            fmax = _get_quartus_fmax()
            logger.info(
                'Quartus fitting & timing done {}, {}.'
                .format(quartus_stats, fmax))
    except Exception as e:
        logger.error(d, e)
    else:
        shutil.rmtree(d)
    return code, legup_stats, quartus_stats, fmax


def report(emir, file_name):
    def sub_report(result):
        stats = _reanalyze_resource_estimates(result, emir)
        samples = _generate_samples(emir['inputs'], 100)
        ana_error = _reanalyze_error_estimate(result, emir)
        sim_error = _run_simulation(
            result.expression, samples, emir['outputs'])
        with logger.context.local(pause_level=logger.levels.off):
            try:
                _, _, quartus_stats, fmax = legup_and_quartus(
                    result.expression, emir['inputs'], emir['outputs'])
                q_lut = quartus_stats.lut
                q_ff = quartus_stats.ff
                q_dsp = quartus_stats.dsp
            except Exception as e:
                logger.error(
                    'Failed to run LegUp and Quartus synthesis', e)
                q_lut = q_ff = q_dsp = fmax = None
        return {
            'Accuracy': {
                'Error Bound': float(ana_error),
                'Simulation': float(sim_error),
            },
            'Resources': {
                'Estimated': {
                    'LUTs': stats.lut,
                    'Registers': stats.ff,
                    'DSP Elements': stats.dsp,
                },
                'Actual': {
                    'LUTs': q_lut,
                    'Registers': q_ff,
                    'DSP Elements': q_dsp,
                },
            },
            'Performance': {
                'Fmax': fmax,
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
