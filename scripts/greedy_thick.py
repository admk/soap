import json
import os
import pickle
from glob import glob

from soap import logger
from soap.context import context
from soap.shell.utils import optimize, report
from soap.analysis.utils import Plot

logger.set_context(level=logger.levels.debug)


for soap_file in glob('examples/multi_expr.soap'):
    plot = Plot(legend_time=True)
    for alg in ['greedy', 'thick']:
        logger.info(soap_file, alg)
        emir_file = '{}.{}.emir'.format(soap_file, alg)
        if os.path.isfile(emir_file):
            with open(emir_file, 'rb') as f:
                emir = pickle.load(f)
        else:
            with context.local(algorithm=alg):
                emir = optimize(soap_file, file_name=None)
            with open(emir_file, 'wb') as f:
                pickle.dump(emir, f)
        report_file = emir_file + '.rpt'
        if not os.path.isfile(report_file):
            with open(report_file, 'w'):
                rpt = report(emir, soap_file)
                rpt = json.dumps(
                    rpt, sort_keys=True, indent=4, separators=(',', ': '))
                f.write(rpt)
        results = emir['results']
        original = [emir['original']]
        func_name = emir['context'].algorithm
        plot.add(results, legend=func_name, time=emir['time'])
    plot.add(original, marker='o', frontier=False, legend='original')
    plot.save('{}.pdf'.format(soap_file))
