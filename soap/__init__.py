__version__ = '2.0.dev'
__author__ = 'Xitong Gao'
__email__ = '@'.join(['xtg08', 'ic.ac.uk'])
__executable__ = 'soapir'
__doc__ = """
SOAP {__version__}
Structural Optimization of Arithmetic Programs.
{__author__} ({__email__})

Usage:
    {__executable__} analyze [options] (<file> | -)
    {__executable__} optimize [options] (<file> | -)
    {__executable__} (-i | --interactive)
    {__executable__} (-h | --help)
    {__executable__} --version

Options:
    -h --help               Show this help message.
    --version               Show version number.
    -i --interactive        Start interactive IPython shell.
    --precision=<width>     Specify the floating-point precision used.
    --single                Use single-precision format, overrides the option
                            `--precision=<width>`.
    --double                Use double-precision format, overrides both options
                            `--precision=<width>` and `--single`.
    -s --simple             Parse using the simple language syntax definition.
                            If not specified, use standard Python syntax
                            instead and use the `ast` module to perform
                            parsing.
    -v --verbose            Do a verbose execution.
    -d --debug              Show debug information, also enable `--verbose`.
""".format(**locals())


try:
    from IPython.core import ultratb
except ImportError:
    pass
else:
    import sys
    sys.excepthook = ultratb.VerboseTB()


import gmpy2

from soap.context import context
from soap.analysis import analyse, frontier, Plot, plot, analyse_and_plot
from soap.parser import pyexpr, pyflow, parse
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
