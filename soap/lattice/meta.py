import abc


class LatticeMeta(abc.ABCMeta):
    """
    The metaclass of lattices.

    It defines the behaviour of the systematic design of lattices.
    """
    def __add__(self, other):
        from soap.lattice.unified_summation import UnifiedSummationLattice

        class SumLat(UnifiedSummationLattice):
            __slots__ = ()
            self_class = self
            other_class = other

        SumLat.__name__ = 'UnifiedSummationLattice_{}_{}'.format(
            self.__name__, other.__name__)
        return SumLat

    def __mul__(self, other):
        from soap.lattice.component_wise import ComponentWiseLattice

        class CompLat(ComponentWiseLattice):
            __slots__ = ()
            _component_classes = (self, other)

        CompLat.__name__ = 'ComponentWiseLattice_{}_{}'.format(
            self.__name__, other.__name__)
        return CompLat
