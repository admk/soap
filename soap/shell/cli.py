import sys

from docopt import docopt

import soap
from soap import logger
from soap.context import context
from soap.parser import parse
from soap.program import Flow
from soap.shell import interactive


usage = """
{__soap__} {__version__} {__date__}
{__description__}
{__author__} ({__email__})

Usage:
    {__executable__} analyze error [options] (<file> | --command=<str> | -)
    {__executable__} analyze resource [options] (<file> | --command=<str> | -)
    {__executable__} optimize [options] (<file> | --command=<str> | -)
    {__executable__} interactive [options]
    {__executable__} lint [--syntax=<str>] (<file> | --command=<str> | -)
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
    --state=<str>           The variable input ranges, a JSON dictionary
                            object.  If specifed, overrides the input
                            statement in the program to be optimized.
                            [default: ]
    --out-vars=<str>        A JSON list object that specifies the output
                            variables and the ordering of these. If specifed,
                            overrides the output statement in the program to be
                            optimized.  [default: ]
    --algorithm=<str>       The name of the algorithm used for optimization.
                            Allows: `closure`, `expand`, `reduce`, `parsings`,
                            `greedy` or `frontier`.  [default: greedy]
    --norm={context.norm}
                            Specify the name of the norm function to use.
                            Allows: `mean_error`, `mse_error`, `max_error`
                            and `geomean`.  [default: {context.norm}]
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
    else:
        file = args['<file>']
        try:
            file = sys.stdin if file == '-' else open(file)
        except FileNotFoundError:
            raise CommandError('File {!r} does not exist'.format(file))
        file = file.read()
    if not file:
        raise CommandError('Empty input')
    return file


def _state(flow, args):
    if isinstance(flow, Flow):
        state = flow.inputs()
        if state:
            return state
    state = args['--state']
    if state:
        return eval(state)
    return {}


def _out_vars(flow, args):
    from soap.expression import Variable
    if isinstance(flow, Flow):
        out_vars = flow.outputs()
        if out_vars:
            return out_vars
    out_vars = args['--out-vars']
    if out_vars:
        return [Variable(v) for v in eval(out_vars)]
    return None


def _analyze(args):
    if not args['analyze']:
        return
    flow = parse(_file(args))
    state = _state(flow, args)
    if args['error']:
        print(flow.debug(state))
    if args['resource']:
        from soap.semantics import BoxState, flow_to_meta_state, luts
        out_vars = _out_vars(flow, args)
        print(luts(flow_to_meta_state(flow), BoxState(state), out_vars))
    return 0


def _optimize(args):
    if not args['optimize']:
        return

    from soap.expression import is_expression
    from soap.semantics import flow_to_meta_state

    def _algorithm(args):
        from soap.transformer import (
            closure, expand, parsings, reduce, greedy, frontier
        )
        algorithm = args['--algorithm']
        algorithm_map = {
            'closure': lambda s, _1, _2: closure(s),
            'expand': lambda s, _1, _2: expand(s),
            'parsings': lambda s, _1, _2: parsings(s),
            'reduce': lambda s, _1, _2: reduce(s),
            'greedy': greedy,
            'frontier': frontier,
        }
        return algorithm_map[algorithm]

    flow = parse(_file(args))
    state = _state(flow, args)
    out_vars = _out_vars(flow, args)
    if not is_expression(flow):
        flow = flow_to_meta_state(flow)
    func = _algorithm(args)
    frontier = func(flow, state, out_vars)
    for r in frontier:
        print(r)

    return 0


def _lint(args):
    if not args['lint']:
        return
    flow = parse(_file(args))
    print(flow)
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
