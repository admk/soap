import builtins
import contextlib
import inspect
import os

import gmpy2
gmpy2.set_context(gmpy2.ieee(64))

import soap
from soap.context.base import _Context, ConfigError
from soap.shell import shell


_repr = builtins.repr
_str = builtins.str
_soap_classes = [c for c in dir(soap) if inspect.isclass(c)]


def _run_line_magic(magic, value):
    with open(os.devnull, 'w') as null:
        with contextlib.redirect_stdout(null):
            shell.run_line_magic(magic, value)


class SoapContext(_Context):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for c in _soap_classes:
            c._repr = c.__repr__

    def precision_hook(self, value):
        fp_format = {'single': 32, 'double': 64}.get(value, None)
        if fp_format is not None:
            value = gmpy2.ieee(fp_format).precision - 1
        gmpy2.get_context().precision = value + 1
        return value

    def repr_hook(self, value):
        str_to_func = {'repr': _repr, 'str': _str}
        value = str_to_func.get(value, value)
        if value == _repr:
            builtins.repr = _repr
            for c in _soap_classes:
                c.__repr__ = c._repr
        elif value == _str:
            builtins.repr = str
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
        _run_line_magic('xmode', value)
        return value

    def autocall_hook(self, value):
        value = bool(value)
        _run_line_magic('autocall', str(int(value)))
        return value
