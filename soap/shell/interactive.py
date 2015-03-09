import sys
from pprint import pprint

import IPython

import soap
from soap.shell.ast import FlowTransformer, TraceTransformer


sys.excepthook = soap.excepthook


class Shell(IPython.terminal.embed.InteractiveShellEmbed):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        banner = '{name} {version} by {author} ({email})\n{desc}'.format(
            name=soap.__soap__, version=soap.__version__,
            author=soap.__author__, email=soap.__email__,
            desc=soap.__description__)
        self.banner1 += '\n'.join(['', banner, ''])
        self.ast_transformers.extend([
            FlowTransformer(self), TraceTransformer(self),
        ])

    def run_cell(self, raw_cell,
                 store_history=False, silent=False, shell_futures=True):
        self.raw_cell = raw_cell
        super().run_cell(raw_cell, store_history, silent, shell_futures)


shell = Shell()


def main(script=None):
    from soap import (
        context, parse, analyze, frontier, Plot, plot, analyze_and_plot,
        parse, expr_parse, Flow, generate, IntegerInterval, FloatInterval,
        FractionInterval, ErrorSemantics, BoxState, IdentifierBoxState,
        MetaState, flow_to_meta_state, mpz, mpq, mpfr, mpz_type, mpq_type,
        mpfr_type, inf, ulp, cast, arith_eval, error_eval, label, luts,
        closure, greedy_frontier_closure, expand, reduce, parsings, martel,
        greedy, frontier,
    )

    def pp(*args):
        for a in args:
            pprint(a)

    def pr(*args):
        with context.local(repr='repr'):
            pp(*args)

    def ps(*args):
        with context.local(repr='str'):
            pp(*args)

    class __IntervalShortcut(object):
        def __init__(self, cls):
            self.cls = cls

        def __getitem__(self, key):
            return self.cls(key)

    I = Int = IntegerInterval
    F = Float = FloatInterval
    E = Error = ErrorSemantics
    S = Box = BoxState
    M = Meta = MetaState
    i = __IntervalShortcut(IntegerInterval)
    f = __IntervalShortcut(FloatInterval)
    e = __IntervalShortcut(ErrorSemantics)
    s = BoxState()
    m = MetaState()
    ctx = context
    [I, Int, F, Float, E, Error, S, Box, M, Meta, i, f, e, s, m, ctx]

    with context.no_invalidate_cache():
        context.repr = str

    if script:
        exec(script)
        shell.banner1 = ''
    return shell()
