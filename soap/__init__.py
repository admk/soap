import os
import sys

__soap__ = 'SOAP'
__description__ = 'Structural Optimization of Arithmetic Programs.'
__version__ = '2.0.dev'
__date__ = 'TBA'
__author__ = 'Xitong Gao'
__email__ = '@'.join(['xtg08', 'ic.ac.uk'])
__executable__ = os.path.basename(sys.argv[0])
__doc__ = """
{__soap__} {__version__} {__date__}
{__description__}
{__author__} ({__email__})
""".format(**locals())


def excepthook(type, value, traceback):
    rv = ultratb.VerboseTB(include_vars=False)(type, value, traceback)
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
    sys.excepthook = excepthook


import gmpy2

from soap.context import context
from soap.analysis import analyze, frontier, Plot, plot, analyze_and_plot
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
