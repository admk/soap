import builtins
import inspect

import gmpy2
gmpy2.set_context(gmpy2.ieee(64))

import soap
from soap.context.base import _Context, ConfigError
from soap.shell import shell


_old_repr = builtins.repr
_soap_classes = [c for c in dir(soap) if inspect.isclass(c)]


class SoapContext(_Context):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for c in _soap_classes:
            c._old_repr = c.__repr__

    def precision_hook(self, value):
        fp_format = {'single': 32, 'double': 64}.get(value, None)
        if fp_format is not None:
            value = gmpy2.ieee(fp_format).precision - 1
        gmpy2.get_context().precision = value + 1
        return value

    def repr_hook(self, value):
        if value in ['repr', repr]:
            builtins.repr = _old_repr
            for c in _soap_classes:
                c.__repr__ = c._old_repr
        elif value in ['str', str]:
            builtins.repr = builtins.str
            for c in _soap_classes:
                c.__repr__ = c.__str__
        else:
            raise ValueError(
                'Attribute repr cannot accept value {}'.format(value))
        return value

    def xmode_hook(self, value):
        allowed = ['plain', 'verbose', 'context']
        if value not in allowed:
            raise ConfigError(
                'Config xmode must take values in {allowed}'
                .format(allowed=allowed))
        shell.run_line_magic('xmode', value)
        return value

    def autocall_hook(self, value):
        shell.run_line_magic('autocall', str(1 if value else 0))
        return bool(value)
