#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


from . import Lattice


class Area(Lattice):

    def __init__(self, e):
        self.e = e
        self.l, self.s = e.as_labels()
        super(Area, self).__init__()

    def join(self, other):
        pass

    def meet(self, other):
        pass

    def __add__(self, other):
        return Area(self.e + other.e)

    def __sub__(self, other):
        return Area(self.e - other.e)

    def __mul__(self, other):
        return Area(self.e * other.e)
