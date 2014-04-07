import builtins

import gmpy2
gmpy2.set_context(gmpy2.ieee(64))

from soap.context.base import _Context


_old_repr = builtins.repr


class SoapContext(_Context):
    def precision_hook(self, key, value):
        fp_format = {'single': 32, 'double': 64}.get(value, None)
        if fp_format is not None:
            value = gmpy2.ieee(fp_format).precision - 1
        gmpy2.get_context().precision = value + 1
        return key, value

    def repr_hook(self, key, value):
        if value in ['repr', repr]:
            builtins.repr = _old_repr
        elif value in ['str', str]:
            builtins.repr = builtins.str
        else:
            raise ValueError(
                'Attribute repr cannot accept value {}'.format(value))
        return key, value
