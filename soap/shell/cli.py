import sys

from docopt import docopt

import soap
from soap import logger
from soap.context import context
from soap.shell import interactive


def _setup_logger(args):
    if args['--verbose']:
        logger.set_context(level=logger.levels.info)
    if args['--debug']:
        logger.set_context(level=logger.levels.debug)
    logger.debug('CLI options: \n', args)


def _setup_precision(args):
    precision = args['--precision']
    if precision:
        context.precision = int(precision)

    single_precision = args['--single']
    if single_precision:
        context.precision = 'single'

    double_precision = args['--double']
    if double_precision:
        context.precision = 'double'


def _interactive(args):
    if args['interactive']:
        interactive.main()
        return 0


def _file(args):
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
    if args['--simple']:
        return soap.parser.program.parse
    return soap.parser.python.pyflow


def _analyze(args):
    def analyze_and_exit(program):
        parse = _parser(args)
        print(parse(program).debug())
        return 0

    if args['analyze']:
        file = _file(args)
        if file == -1:
            return -1
        return analyze_and_exit(file)


def _optimize(args):
    if args['optimize']:
        logger.error('Interface for optimization is not implemented.')
    return -1


def _unreachable(args):
    # did not complete
    return -1


def main():
    args = docopt(soap.__doc__, version=soap.__version__)
    functions = [
        _setup_logger, _setup_precision, _interactive, _analyze, _optimize,
        _unreachable
    ]
    for f in functions:
        return_code = f(args)
        if return_code is not None:
            sys.exit(return_code)


if __name__ == '__main__':
    main()
