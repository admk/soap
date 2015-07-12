import os
import sys

__soap__ = 'SOAP'
__description__ = """
Numerical program structural optimizer."""
__version__ = '2.0.1'
__date__ = '23 Feb 2015'
__author__ = 'Xitong Gao'
__email__ = '@'.join(['xtg08', 'ic.ac.uk'])
__executable__ = os.path.basename(sys.argv[0])
__doc__ = """
{__soap__} {__version__} {__date__}
{__description__}
{__author__} ({__email__})
""".format(**locals())


from soap import logger
from soap.context import context
from soap.analysis import analyze, frontier, Plot, plot
from soap.parser import parse, expr_parse
from soap.program import Flow, generate
from soap.semantics import (
    IntegerInterval, FloatInterval, ErrorSemantics, BoxState, MetaState,
    flow_to_meta_state, mpz, mpq, mpfr, mpz_type, mpq_type, mpfr_type, inf,
    ulp, cast, arith_eval, error_eval, label, luts
)
from soap.transformer import (
    closure, greedy_frontier_closure, expand, reduce, parsings, greedy
)


def excepthook(type, value, traceback):
    rv = ultratb.VerboseTB(include_vars=False)(type, value, traceback)
    if context.ipdb:
        from IPython.core.debugger import Pdb
        from soap.shell import shell
        logger.info('Launching Pdb...')
        pdb = Pdb(shell.colors)
        pdb.interaction(None, traceback)
    return rv


try:
    from IPython.core import ultratb
except ImportError:
    pass
else:
    sys.excepthook = excepthook
