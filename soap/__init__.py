"""
SOAP
====

Structural Optimization of Arithmetic Programs.
"""
__version__ = '2.0.dev'
__author__ = 'Xitong Gao'
__email__ = '@'.join(['xtg08', 'ic.ac.uk'])


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
