import sys
from pprint import pformat


class levels():
    pass
levels = levels()


labels = ['debug', 'info', 'warning', 'error', 'off']
for i, l in enumerate(labels):
    levels.__dict__[l] = i


context = {
    'level': levels.off,
    'file': None,
    'persistent': {},
}


def set_context(**kwargs):
    context.update(kwargs)


def get_context():
    return context


def format(*args):
    return ' '.join(pformat(a) if not isinstance(a, str) else a for a in args)


def log(*args, l=levels.info):
    if l < get_context()['level']:
        return
    f = context['file'] or sys.stdout
    print(format(*args), end='', file=f)


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
        s.append(k + ': ' + ','.join(format(*v)))
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


labels = ['debug', 'info', 'warning', 'error', 'off']
for i, l in enumerate(labels):
    globals()[l] = log_level(i)(line)
    globals()[l + '_enable'] = log_enable(i)


if __name__ == '__main__':
    info('Hello')
    debug('Hello')
    import time
    debug_enable(time.sleep)(100)
