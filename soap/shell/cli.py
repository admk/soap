import pickle
import sys

from docopt import docopt

import soap
from soap import logger
from soap.context import context
from soap.shell import interactive
from soap.shell.utils import (
    analyze_error, analyze_resource, optimize, parse, plot
)


usage = """
{__soap__} {__version__} {__date__}
{__description__}
{__author__} ({__email__})

Usage:
    {__executable__} analyze error [options] (<file> | --command=<str> | -)
    {__executable__} analyze resource [options] (<file> | --command=<str> | -)
    {__executable__} optimize [options] (<file> | --command=<str> | -)
    {__executable__} plot <file>
    {__executable__} interactive [options]
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
                            `greedy`, `frontier` or `thick`.  [default: thick]
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

    context.unroll_factor = int(args['--unroll-factor'])
    context.widen_factor = int(args['--widen-factor'])
    context.window_depth = int(args['--window-depth'])
    context.unroll_depth = int(args['--unroll-depth'])

    context.norm = args['--norm']

    if args['--no-multiprocessing']:
        context.multiprocessing = False


def _interactive(args):
    if not args['interactive']:
        return
    interactive.main()
    return 0


def _file(args):
    command = args['--command']
    if command:
        file = command
        out_file = 'from_command'
    else:
        file = args['<file>']
        try:
            if file == '-':
                out_file = 'from_stdin'
                file = sys.stdin
            else:
                out_file = file
                file = open(file)
        except FileNotFoundError:
            raise CommandError('File {!r} does not exist'.format(file))
        file = file.read()
    if not file:
        raise CommandError('Empty input')
    return file, out_file


def _analyze(args):
    if not args['analyze']:
        return
    file, out_file = _file(args)
    if args['error']:
        result = analyze_error(file)
        out_file = '{}.acc'.format(out_file)
    if args['resource']:
        result = analyze_resource(file)
        out_file = '{}.res'.format(out_file)
    logger.debug(result)
    with open(out_file, 'w') as f:
        f.write(str(result))
    return 0


def _optimize(args):
    if not args['optimize']:
        return
    file, out_file = _file(args)
    results = optimize(file)
    for r in results:
        logger.debug(str(r))
    with open('{}.emir'.format(out_file), 'wb') as f:
        pickle.dump(results, f)
    if args['--plot']:
        plot(results, out_file)
    return 0


def _plot(args):
    if not args['plot']:
        return
    file, out_file = _file(args)
    emir = pickle.loads(file)
    plot(emir, out_file)
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
        _setup_context, _interactive, _analyze, _optimize, _lint, _unreachable,
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
