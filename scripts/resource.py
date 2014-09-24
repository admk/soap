import re
import os
import pickle
import shutil
import tempfile
from collections import namedtuple
from glob import glob

import sh
from akpytemp.utils import code_gobble

from soap import logger
from soap.context import context
from soap.flopoco.common import cd
from soap.program.generator.c import generate_function
from soap.semantics.functions.label import resources
from soap.shell.utils import parse


logger.set_context(level=logger.levels.info)


def wrap_in_main(iv, func):
    code = code_gobble(
        """
        {}

        int main() {{
            float rv = func({});
            return 0;
        }}
        """).format(func, ', '.join('1' for _ in iv))
    return code


legup_path = os.path.expanduser('~/legup/examples')

makefile = code_gobble(
    """
    NAME=test
    FAMILY=StratixIV
    NO_OPT=1
    NO_INLINE=1
    LEVEL={}
    include $(LEVEL)/Makefile.common
    """).format(legup_path)
s = namedtuple('Statistics', ['dsp', 'ff', 'lut'])


def get_stats():
    with open('resources.legup.rpt') as f:
        file = f.read()
    dsp = int(re.search('DSP Elements: (\d+)', file).groups()[0])
    ff = int(re.search('Registers: (\d+)', file).groups()[0])
    lut = int(re.search('Combinational: (\d+)', file).groups()[0])
    return s(dsp, ff, lut)


def legup(code):
    d = tempfile.mktemp(suffix='/')
    try:
        with cd(d):
            with open('test.c', 'w') as f:
                f.write(code)
            with open('Makefile', 'w') as f:
                f.write(makefile)
            sh.make(_out='make.log', _err='make.err.log')
            stats = get_stats()
    except sh.ErrorReturnCode:
        raise
    else:
        return stats
    finally:
        print(d)
        # shutil.rmtree(d)


results = []
for emir in glob('examples/*.emir'):
    logger.info(emir)
    soap_file = os.path.splitext(emir)[0]
    with open(soap_file) as f:
        p, iv, rv = parse(f.read())
    with open(emir, 'rb') as f:
        emir = pickle.load(f)
        for r in emir['results']:
            func = generate_function(r.expression, iv, rv, 'func')
            code = wrap_in_main(iv, func)
            legup_stats = legup(code)
            soap_stats = resources(r.expression, iv, rv, context.precision)
            results.append({
                'soap_area': soap_stats,
                'legup_area': legup_stats,
                'mir': r.expression,
                'code': code,
            })
            logger.info(soap_stats, legup_stats)
            import ipdb; ipdb.set_trace()
