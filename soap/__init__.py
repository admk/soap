__version__ = '2.0.dev'
__date__ = 'TBA'
__author__ = 'Xitong Gao'
__email__ = '@'.join(['xtg08', 'ic.ac.uk'])


def excepthook(type, value, traceback):
    rv = ultratb.VerboseTB()(type, value, traceback)
    if context.ipdb:
        from IPython.core.debugger import Pdb
        from soap.shell import shell
        pdb = Pdb(shell.colors)
        pdb.interaction(None, traceback)
    return rv


try:
    from IPython.core import ultratb
except ImportError:
    pass
else:
    import sys
    sys.excepthook = excepthook


import os
import sys

import gmpy2

from soap.context import context
from soap.analysis import analyse, frontier, Plot, plot, analyse_and_plot
from soap.parser import pyparse, parse
from soap.program import Flow, meta_state_to_flow
from soap.semantics import (
    IntegerInterval, FloatInterval, FractionInterval, ErrorSemantics,
    BoxState, IdentifierBoxState, MetaState, flow_to_meta_state,
    mpz, mpq, mpfr, mpz_type, mpq_type, mpfr_type, inf, ulp, cast,
    arith_eval, error_eval, label, luts
)
from soap.transformer import (
    closure, greedy_frontier_closure, expand, reduce, parsings,
    martel, greedy, frontier,
)


__executable__ = os.path.basename(sys.argv[0])
__doc__ = """
SOAP {__version__} {__date__}
Structural Optimization of Arithmetic Programs.
{__author__} ({__email__})

Usage:
    {__executable__} analyze [options] (<file> | --command=<str> | -)
    {__executable__} optimize [options] (<file> | --command=<str> | -)
    {__executable__} interactive [options]
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
    --syntax=<str>          Parse using the specified language syntax
                            definition.  Allowed options are: `python` and
                            `simple`.  If not specified, use standard Python
                            syntax instead and use the `ast` module to perform
                            parsing.  [default: simple]
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
                            object.  [default: ]
    --state-file=<str>      The variable input ranges, a file containing a JSON
                            dictionary object.  Overrides `--state`.
    --out-vars=<str>        A JSON list object that specifies the output
                            variables and the ordering of these.  [default: ]
    --out-vars-file=<str>   A file containing the JSON list object that
                            specifies the output variables and the ordering of
                            these.  Overrides `--out-vars`.
    --algorithm=<str>       The name of the algorithm used for optimization.
                            Allows: `closure`, `expand`, `reduce`, `parsings`,
                            `greedy` or `frontier`.  [default: greedy]
    --ipdb                  Launch ipdb interactive prompt on exceptions.
    --no-error              Silent all errors.  Overrides `--no-warning`,
                            `--verbose` and `--debug`.
    --no-warning            Silent all warnings.  Overrides `--verbose` and
                            `--debug`.
    -v --verbose            Do a verbose execution.
    -d --debug              Show debug information, also enable `--verbose`.
""".format(**locals())
