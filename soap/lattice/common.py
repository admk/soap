"""
.. module:: soap.lattice.common
    :synopsis: The common utilities for lattices.
"""


def _lattice_factory(cls, lattice_cls, name):
    is_class = callable(cls)
    try:
        is_class_list = all(callable(c) for c in cls)
    except (TypeError, ValueError):
        is_class_list = False

    class L(lattice_cls):
        __slots__ = ()

        def _class(self):
            return cls

        def _cast_value(self, v=None, top=False, bottom=False):
            if cls is None:
                return v
            if isinstance(v, str):
                if v == 'top':
                    top = True
                elif v == 'bottom':
                    bottom = True
            if top or bottom:
                if is_class:
                    return cls(top=top, bottom=bottom)
                if is_class_list:
                    return cls[0](top=top, bottom=bottom)
                raise TypeError('Do not know how to cast into top or bottom')
            if is_class:
                if isinstance(v, cls):
                    return v
                return cls(v)
            if is_class_list:
                if isinstance(v, cls):
                    return v
                for c in cls:
                    try:
                        return c(v)
                    except Exception:
                        pass
                raise ValueError('Cannot convert value to any of the classes')
            if v not in cls:
                raise ValueError('Non-existing element: %r' % v)
            return v

    if name:
        L.__name__ = name
    return L
