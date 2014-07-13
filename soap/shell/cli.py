import sys

from docopt import docopt

import soap
from soap import logger
from soap.context import context
from soap.shell import interactive


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
            logger.error('File {!r} does not exist'.format(file))
            return -1
        file = file.read()
    if not file:
        logger.error('Empty input')
        return -1
    return file


def _parser(args):
    syntax = args['--syntax']
    syntax_map = {
        'python': soap.parser.python.pyparse,
        'simple': soap.parser.program.parse,
    }
    return syntax_map[syntax]


def _analyze(args):
    if not args['analyze']:
        return
    file = _file(args)
    if file == -1:
        return -1
    parse = _parser(args)
    print(parse(file).debug())
    return 0


def _optimize(args):
    if not args['optimize']:
        return

    from soap.expression import is_expression, Variable
    from soap.semantics import flow_to_meta_state

    def _state(args):
        state_file = args['--state-file']
        if state_file:
            state = open(state_file).read()
        else:
            state = args['--state']
        if not state:
            return {}
        return eval(state)

    def _out_vars(args):
        out_vars_file = args['--out-vars-file']
        if out_vars_file:
            out_vars = open(out_vars_file).read()
        else:
            out_vars = args['--out-vars']
        if not out_vars:
            return None
        out_vars = [Variable(v) for v in eval(out_vars)]
        return out_vars

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

    file = _file(args)
    if file == -1:
        return -1

    flow = _parser(args)(file)
    if not is_expression(flow):
        flow = flow_to_meta_state(flow)

    state = _state(args)
    out_vars = _out_vars(args)
    func = _algorithm(args)
    results = func(flow, state, out_vars)
    for r in results:
        print(r)

    return 0


def _unreachable(args):
    # did not complete
    return -1


def main():
    args = docopt(soap.__doc__, version=soap.__version__)
    functions = [
        _setup_context, _interactive, _analyze, _optimize, _unreachable
    ]
    for f in functions:
        return_code = f(args)
        if return_code is not None:
            sys.exit(return_code)


if __name__ == '__main__':
    main()
