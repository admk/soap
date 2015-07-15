import json
import pickle
import sys

from docopt import docopt

import soap
from soap import logger
from soap.analysis import analyze
from soap.context import context
from soap.semantics import flow_to_meta_state
from soap.shell import interactive
from soap.shell.utils import (
    optimize, parse, plot, emir2csv, report, simulate_error
)


usage = """
{__soap__} {__version__} {__date__}
{__description__}
{__author__} ({__email__})

Usage:
    {__executable__} analyze [options] (<file> | --command=<str> | -)
    {__executable__} simulate [options] (<file> | --command=<str> | -)
    {__executable__} optimize [options] (<file> | --command=<str> | -)
    {__executable__} plot [options] <file>
    {__executable__} csv [options] <file>
    {__executable__} report [options] <file>
    {__executable__} interact [options] [<file>]
    {__executable__} lint [options] (<file> | --command=<str> | -)
    {__executable__} (-h | --help)
    {__executable__} --version

Options:
    -h --help               Show this help message.
    --version               Show version number.
    -c --command=<str>      Instead of specifying a file name, analyze or
                            optimize the command provided by this option.
    --precision={context.precision}
                            Specify the floating-point precision used.  Allows:
                            `single` (23), `double` (52), or integers.
                            [default: {context.precision}]
    --single                Use single-precision format, overrides the option
                            `--precision=<width>`.
    --double                Use double-precision format, overrides both options
                            `--precision=<width>` and `--single`.
    --population-size=<int> Simulation is used to find actual bound on errors.
                            This parameter specifies the population size for
                            simulation.  [default: 100]
    --fast-factor={context.fast_factor}
                            Reduce the number of iterations taken by error
                            analysis with a factor.  Only values less than 1
                            have effect.  [default: {context.fast_factor}]
    --unroll-factor={context.unroll_factor}
                            Set the number of iterations bofore stopping loop
                            unroll and use the loop invariant in loop analysis.
                            [default: {context.unroll_factor}]
    --widen-factor={context.widen_factor}
                            Set the number of iterations before using widening
                            in loop analysis.
                            [default: {context.widen_factor}]
    --window-depth={context.window_depth}
                            Set the depth limit window of structural
                            optimization.  [default: {context.window_depth}]
    --unroll-depth={context.unroll_depth}
                            Set the loop unrolling depth.
                            [default: {context.unroll_depth}]
    --algorithm=<str>       The name of the algorithm used for optimization.
                            Allows: `closure`, `expand`, `reduce`, `parsings`,
                            `greedy`, `frontier`, `thick` or `partition`.
                            [default: partition]
    --norm={context.norm}
                            Specify the name of the norm function to use.
                            Allows: `mean_error`, `mse_error`, `max_error`
                            and `geomean`.  [default: {context.norm}]
    --plot                  Plot results.
    --no-multiprocessing    Disable multiprocessing.
    --ipdb                  Launch ipdb interactive prompt on exceptions.
    --no-error              Silent all errors.  Overrides `--no-warning`,
                            `--verbose` and `--debug`.
    --no-warning            Silent all warnings.  Overrides `--verbose` and
                            `--debug`.
    --dump-cache-info       Show cache statistics on exit.
    -v --verbose            Do a verbose execution.
    -d --debug              Show debug information, also enable `--verbose`.
""".format(**vars(soap))


class CommandError(Exception):
    """Failed to execute command.  """


def _setup_context(args):
    context.ipdb = args['--ipdb']

    if args['--verbose']:
        logger.set_context(level=logger.levels.info)
    if args['--debug']:
        logger.set_context(level=logger.levels.debug)
    if args['--no-warning']:
        logger.set_context(level=logger.levels.error)
    if args['--no-error']:
        logger.set_context(level=logger.levels.off)
    logger.debug('CLI options: \n', args)

    precision = args['--precision']
    if precision:
        context.precision = int(precision)

    single_precision = args['--single']
    if single_precision:
        context.precision = 'single'

    double_precision = args['--double']
    if double_precision:
        context.precision = 'double'

    algorithm = args['--algorithm']
    if algorithm:
        context.algorithm = algorithm

    context.fast_factor = float(args['--fast-factor'])
    context.unroll_factor = int(args['--unroll-factor'])
    context.widen_factor = int(args['--widen-factor'])
    context.window_depth = int(args['--window-depth'])
    context.unroll_depth = int(args['--unroll-depth'])
    context.norm = args['--norm']

    if args['--no-multiprocessing']:
        context.multiprocessing = False


def _file(args):
    command = args['--command']
    if command:
        return command, 'from_command'
    file = args['<file>']
    if not file:
        return None, None
    if file == '-':
        out_file = 'from_stdin'
        file = sys.stdin
    else:
        out_file = file
        try:
            file = open(file)
        except FileNotFoundError:
            raise CommandError('File {!r} does not exist'.format(file))
    file = file.read()
    if not file:
        raise CommandError('Empty input')
    return file, out_file


def _interact(args):
    if not args['interact']:
        return
    interactive.main(args['<file>'])
    return 0


def _analyze(args):
    if not args['analyze']:
        return
    file, out_file = _file(args)
    prog, inputs, outputs = parse(file)
    result = analyze([flow_to_meta_state(prog)], inputs, outputs).pop()
    out_file = '{}.rpt'.format(out_file)
    logger.debug(result)
    with open(out_file, 'w') as f:
        f.write(str(result))
    return 0


def _simulate(args):
    if not args['simulate']:
        return
    file, out_file = _file(args)
    return simulate_error(file, int(args['--population-size']))


def _optimize(args):
    if not args['optimize']:
        return
    file, out_file = _file(args)
    emir = optimize(file, out_file)
    for r in emir['results']:
        logger.debug(str(r))
    logger.debug(emir['original'])
    logger.debug('Time:', emir['time'])
    with open('{}.emir'.format(out_file), 'wb') as f:
        pickle.dump(emir, f)
    if args['--plot']:
        plot(emir, out_file)
    return 0


def _plot(args):
    if not args['plot']:
        return
    file = args['<file>']
    with open(file, 'rb') as f:
        emir = pickle.load(f)
    plot(emir, file)
    return 0


def _csv(args):
    if not args['csv']:
        return
    file = args['<file>']
    with open(file, 'rb') as f:
        emir = pickle.load(f)
    csv_file = emir['file'] + '.csv'
    with open(csv_file, 'w') as f:
        emir2csv(emir, f)
    return 0


def _report(args):
    if not args['report']:
        return
    file = args['<file>']
    with open(file, 'rb') as f:
        emir = pickle.load(f)
    rpt = report(emir, file)
    rpt = json.dumps(rpt, sort_keys=True, indent=4, separators=(',', ': '))
    logger.debug(rpt)
    report_file = emir['file'] + '.rpt'
    with open(report_file, 'w') as f:
        f.write(rpt)
    return 0


def _lint(args):
    if not args['lint']:
        return
    program, _, _ = parse(_file(args))
    logger.debug(program)
    return 0


def _unreachable(args):
    # did not complete
    raise CommandError('This statement should never be reached.')


def _post_run(args):
    if args['--dump-cache-info']:
        from soap.common.cache import dump_cache_info
        with logger.info_context():
            dump_cache_info()


def main():
    args = docopt(usage, version=soap.__version__)
    functions = [
        _setup_context, _interact, _analyze, _simulate, _optimize, _lint,
        _plot, _csv, _report, _unreachable,
    ]
    try:
        for f in functions:
            return_code = f(args)
            if return_code is not None:
                break
        _post_run(args)
        sys.exit(return_code)
    except CommandError as e:
        logger.error(e)
        sys.exit(-1)


if __name__ == '__main__':
    main()
