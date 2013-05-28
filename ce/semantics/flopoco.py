import os

from ce.common import timeit


we_min, we_max = 5, 16
wf_min, wf_max = 10, 113
we_range = list(range(we_min, we_max))
wf_range = list(range(wf_min, wf_max))
default_file = 'ce/semantics/area.pkl'


def get_luts(file_name):
    from bs4 import BeautifulSoup
    with open(file_name, 'r') as f:
        f = BeautifulSoup(f.read())
        app = f.document.application
        util = app.find('section', stringid='XST_DEVICE_UTILIZATION_SUMMARY')
        luts = util.find('item', stringid='XST_NUMBER_OF_SLICE_LUTS')
        return luts.get('value')


@timeit
def _para_synth(op_we_wf):
    import sh
    op, we, wf = op_we_wf
    flo_cmd = []
    if op == 'add':
        flo_cmd += ['FPAdder', we, wf]
    elif op == 'mul':
        flo_cmd += ['FPMultiplier', we, wf, wf]
    wd = 'syn_%d' % os.getpid()
    f = 'flopoco.vhdl'
    g = 'flopoco.ngc'
    h = g + '_xst.xrpt'
    s = sh.echo('run', '-p', 'xc6vlx760',
                '-ifn', f, '-ifmt', 'VHDL', '-ofn', g, '-ofmt', 'NGC')
    try:
        print('Processing', op, we, wf)
        sh.mkdir('-p', wd)
        sh.cd(wd)
        sh.flopoco(*flo_cmd)
        print('Xilinx', op, we, wf)
        sh.xst(s)
        item = dict(op=op, we=we, wf=wf, value=get_luts(h))
        print(item)
    except sh.ErrorReturnCode:
        print('Error processing', op, we, wf)
        item = dict(op=op, we=we, wf=wf, value=-1)
    except KeyboardInterrupt:
        pass
    sh.cd('..')
    sh.rm('-rf', wd)
    return item


pool = None


@timeit
def synth(we_range, wf_range):
    import itertools
    from multiprocessing import Pool
    global pool
    if not pool:
        pool = Pool(8)
    args = itertools.product(['add', 'mul'], we_range, wf_range)
    return list(pool.imap_unordered(_para_synth, args))


def load(file_name):
    import pickle
    with open(file_name, 'rb') as f:
        return pickle.loads(f.read())


def save(file_name, results):
    import pickle
    with open(file_name + '.pkl', 'wb') as f:
        pickle.dump(results, f)


def plot(results):
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    fig = plt.figure()
    ax = Axes3D(fig)
    vl = []
    for i in results:
        xv, yv, zv = int(i['we']), int(i['wf']), int(i['value'])
        if zv < 0:
            continue
        vl.append((xv, yv, zv))
    ax.scatter(*zip(*vl))
    plt.show()


if not os.path.isfile(default_file):
    print('area statistics file does not exist, synthesizing...')
    save(default_file, synth(we_range, wf_range))

add = {}
mul = {}
for i in load(default_file):
    xv, yv, zv = int(i['we']), int(i['wf']), int(i['value'])
    if zv <= 0:
        continue
    if i['op'] == 'add':
        add[xv, yv] = zv
    elif i['op'] == 'mul':
        mul[xv, yv] = zv
keys = sorted(list(set(add.keys()) & set(mul.keys())))


if __name__ == '__main__':
    plot(load(default_file))
