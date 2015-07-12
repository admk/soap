import os
import pickle
from pprint import pprint

import IPython

import soap


class Shell(IPython.terminal.embed.InteractiveShellEmbed):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        banner = '{name} {version} by {author} ({email})\n{desc}'.format(
            name=soap.__soap__, version=soap.__version__,
            author=soap.__author__, email=soap.__email__,
            desc=soap.__description__)
        self.banner1 += '\n'.join(['', banner, ''])

    def run_cell(self, raw_cell,
                 store_history=False, silent=False, shell_futures=True):
        self.raw_cell = raw_cell
        super().run_cell(raw_cell, store_history, silent, shell_futures)


shell = Shell()


def main(file=None):
    from soap import (
        context, analyze, frontier, Plot, plot, parse, Flow, generate,
        IntegerInterval, FloatInterval, ErrorSemantics, BoxState, MetaState,
        flow_to_meta_state, mpz, mpq, mpfr, mpz_type, mpq_type, mpfr_type,
        inf, ulp, cast, arith_eval, error_eval, label, luts, closure,
        greedy_frontier_closure, expand, reduce, parsings, greedy
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

    if not file:
        return shell()
    directory, file_name = os.path.split(file)
    base_name, ext = os.path.splitext(file_name)
    var_name = base_name.replace('.', '_')
    if var_name[0].isdigit():
        var_name = 's' + var_name
    if ext == '.py':
        with open(file, 'r') as f:
            exec(f.read())
        banner = ''
    elif ext == '.emir':
        with open(file, 'rb') as f:
            globals()[var_name] = pickle.loads(f.read())
        banner = (
            shell.banner1 +
            '\nEMIR file loaded and stored in `{}`.'.format(var_name))
    elif ext == '.soap':
        with open(file, 'r') as f:
            globals()[var_name] = parse(f.read())
        banner = (
            shell.banner1 +
            '\nSOAP file loaded and stored in `{}`.'.format(var_name))
    else:
        raise ValueError('Unrecognized file extension {}'.format(ext))
    shell.banner1 = banner
    return shell()
