import json
import os
import pickle
from glob import glob

from soap import logger
from soap.context import context
from soap.shell.utils import optimize, report, _reanalyze_results
from soap.analysis.utils import Plot

logger.set_context(level=logger.levels.debug)
logger.set_context(pause_level=logger.levels.off)


for soap_file in glob('examples/*.soap'):
    lock_file = '{}.lock'.format(soap_file)
    if os.path.isfile(lock_file):
        continue
    lock = open(lock_file, 'w')
    print(soap_file)
    plot = Plot(legend_time=True, legend_pos=(1.0, 1.0))
    for alg in ['greedy', 'thick']:
        logger.info(soap_file, alg)
        emir_file = '{}.{}.emir'.format(soap_file, alg)
        if os.path.isfile(emir_file):
            with open(emir_file, 'rb') as f:
                emir = pickle.load(f)
        else:
            with context.local(algorithm=alg):
                try:
                    emir = optimize(soap_file, file_name=soap_file)
                except Exception as e:
                    logger.error(e)
                    with open('error.log', 'a') as f:
                        f.write('Error in ' + emir_file)
                        f.write(str(e))
                        continue
            with open(emir_file, 'wb') as f:
                pickle.dump(emir, f)
        report_file = emir_file + '.rpt'
        if not os.path.isfile(report_file):
            rpt = report(emir, soap_file)
            rpt = json.dumps(
                rpt, sort_keys=True, indent=4, separators=(',', ': '))
            with open(report_file, 'w') as f:
                f.write(rpt)
        if alg == 'greedy':
            results = emir['results']
            time = emir['time']
        else:
            results = results | emir['results']
        original = [emir['original']]
        func_name = emir['context'].algorithm
    plot.add(results, legend='Frontier', time=time, color='k')
    plot.add(
        original, color='r', marker='o', frontier=False, legend='Original')
    plot_file = '{}.pdf'.format(soap_file)
    plot.save(plot_file)
    lock.close()
