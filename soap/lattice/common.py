"""
.. module:: soap.lattice.common
    :synopsis: The common utilities for lattices.
"""


def _is_class(cls):
    return callable(cls)


def _lattice_factory(cls, lattice_cls, name):
    class L(lattice_cls):
        def _class(self):
            if _is_class(cls):
                return cls

        def _container(self):
            if not _is_class(cls):
                return cls
    if name:
        L.__name__ = name
    return L
