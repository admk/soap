import os
import sys
from pprint import pformat
from contextlib import contextmanager


class levels():
    pass
levels = levels()


labels = ['debug', 'info', 'warning', 'error', 'off']
for i, l in enumerate(labels):
    levels.__dict__[l] = i


colours = {
    levels.debug: '\033[94m',
    levels.info: '\033[92m',
    levels.warning: '\033[93m',
    levels.error: '\033[91m',
}
colours_end = '\033[0m'


context = {
    'level': levels.off,
    'pause_level': levels.off,
    'colour': True,
    'file': None,
    'persistent': {},
}


def set_context(**kwargs):
    context.update(kwargs)


def get_context():
    return context


def colourise(s, l=levels.info):
    if not 'color' in os.environ['TERM']:
        return s
    if not get_context()['colour']:
        return s
    return colours[l] + s + colours_end


def format(*args):
    return ' '.join(pformat(a) if not isinstance(a, str) else a for a in args)


def log(*args, l=levels.info):
    if l < get_context()['level']:
        return
    f = get_context()['file'] or sys.stdout
    print(colourise(format(*args), l), end='', file=f)
    while l >= get_context()['pause_level']:
        r = input('Continue [Return], Stack trace [t], Abort [q]: ')
        if not r:
            break
        if r == 't':
            import traceback
            traceback.print_stack()
        if r == 'q':
            sys.exit(-1)


def line(*args, l=levels.info):
    args += ('\n', )
    log(*args, l=l)


def rewrite(*args, l=levels.info):
    args += ('\r', )
    log(*args, l=l)


def persistent(name, *args, l=levels.info):
    get_context()['persistent'][name] = args + (l, )
    s = []
    for k, v in get_context()['persistent'].items():
        *v, l = v
        s.append(k + ': ' + format(*v))
    s = '; '.join(s)
    s += ' ' * (78 - len(s))
    rewrite(s, l=l)


def unpersistent(*args):
    p = get_context()['persistent']
    for n in args:
        if not n in p:
            continue
        del p[n]


def log_level(l):
    def wrapper(f):
        def wrapped(*args, l=l):
            f(*args, l=l)
        return wrapped
    return wrapper


def log_enable(l):
    def wrapper(f):
        def wrapped(*args, **kwargs):
            if l < get_context()['level']:
                return
            return f(*args, **kwargs)
        return wrapped
    return wrapper


@contextmanager
def local_context(**kwargs):
    ctx = dict(get_context())
    set_context(**kwargs)
    yield
    set_context(**ctx)


labels = ['debug', 'info', 'warning', 'error', 'off']
for i, l in enumerate(labels):
    globals()[l] = log_level(i)(line)
    globals()[l + '_enable'] = log_enable(i)


if __name__ == '__main__':
    set_context(level=levels.debug)
    info('Hello')
    debug('Hello')
    warning('Hello')
    error('Hello')
