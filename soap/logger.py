from __future__ import print_function
import os
import sys
from pprint import pformat
from contextlib import contextmanager

from soap.context import context as _global_context


class levels():
    pass
levels = levels()


for i, l in enumerate(['debug', 'info', 'warning', 'error', 'off']):
    levels.__dict__[l] = i


with _global_context.no_invalidate_cache():
    _global_context.logger = {
        'level': levels.warning,
        'pause_level': levels.off,
        'color': True,
        'file': None,
        'persistent': {},
    }
    context = _global_context.logger


def set_context(**kwargs):
    context.update(kwargs)


def get_context():
    return context


def color(s, l=levels.info):
    colors = {
        levels.debug: '\033[90m',
        levels.info: '\033[92m',
        levels.warning: '\033[93m',
        levels.error: '\033[91m',
    }
    colors_end = '\033[0m'
    if not 'color' in os.environ['TERM']:
        return s
    if not get_context()['color']:
        return s
    return colors[l] + s + colors_end


def format(*args):
    return ' '.join(pformat(a) if not isinstance(a, str) else a for a in args)


def log(*args, **kwargs):
    l = kwargs.get('l', levels.info)
    if l < get_context()['level']:
        return
    f = get_context()['file'] or sys.stdout
    print(color(format(*args), l), end='', file=f)
    while l >= get_context()['pause_level']:
        r = input('Continue [Return], Stack trace [t], Abort [q]: ')
        if not r:
            break
        if r == 't':
            import traceback
            traceback.print_stack()
        if r == 'q':
            sys.exit(-1)


def line(*args, **kwargs):
    l = kwargs.get('l', levels.info)
    args += ('\n', )
    log(*args, l=l)


def rewrite(*args, **kwargs):
    l = kwargs.get('l', levels.info)
    args += ('\r', )
    log(*args, l=l)


def persistent(name, *args, **kwargs):
    l = kwargs.get('l', levels.info)
    prev = get_context()['persistent'].get(name)
    curr = args + (l, )
    if prev == curr:
        return
    get_context()['persistent'][name] = curr
    s = []
    for k, v in get_context()['persistent'].items():
        v = list(v)
        l = v.pop()
        s.append(k + ': ' + format(*v))
    s = '; '.join(s)
    s += ' ' * (78 - len(s))
    s = s[:80]
    rewrite(s, l=l)


def unpersistent(*args):
    p = get_context()['persistent']
    for n in args:
        if not n in p:
            continue
        del p[n]


@contextmanager
def local_context(**kwargs):
    ctx = dict(get_context())
    set_context(**kwargs)
    yield
    set_context(**ctx)


def log_level(l):
    def wrapper(f):
        def wrapped(*args, **kwargs):
            kwargs['l'] = l
            f(*args, **kwargs)
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


def log_context(l):
    def wrapper():
        return local_context(level=l)
    return wrapper


def _init_level():
    l = levels.warning
    if '-v' in sys.argv:
        l = levels.info
    elif '-vv' in sys.argv:
        l = levels.debug
    set_context(level=l)


labels = ['debug', 'info', 'warning', 'error', 'off']
for i, l in enumerate(labels):
    locals()[l] = log_level(i)(line)
    locals()[l + '_enable'] = log_enable(i)
    locals()[l + '_context'] = log_context(i)


_init_level()
