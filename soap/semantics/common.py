"""
.. module:: soap.semantics.common
    :synopsis: Common definitions for semantics.
"""


def is_constant(e):
    from soap.semantics.error import (
        mpz_type, mpfr_type, Interval, ErrorSemantics
    )
    if isinstance(e, (mpz_type, mpfr_type)):
        return True
    if isinstance(e, Interval):
        return e.min == e.max
    if isinstance(e, ErrorSemantics):
        return is_constant(e.v)
    return False


def is_numeral(e):
    from soap.semantics.error import (
        mpz_type, mpfr_type, Interval, ErrorSemantics
    )
    from soap.semantics.linalg import MultiDimensionalArray
    return isinstance(e, (
        mpz_type, mpfr_type, Interval, ErrorSemantics, MultiDimensionalArray))
