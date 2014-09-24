import os
import pickle
from glob import glob

from akpytemp.utils import code_gobble

from soap.shell.utils import parse
from soap.program.generator.c import generate_func


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


def legup(code):
    return


results = []
for emir in glob('examples/*.emir'):
    soap_file = os.path.splitext(emir)[0]
    with open(soap_file) as f:
        p, iv, rv = parse(f.read())
    with open(emir, 'b') as f:
        emir = pickle.load(f)
        for r in emir['results']:
            func = generate_func(r.expression, iv, rv, 'func')
            code = wrap_in_main(iv, func)
            legup_stats = legup(code)
            results.append({
                'estimated': r.area,
                'legup': legup_stats,
                'mir': r.expression,
                'code': code,
            })
