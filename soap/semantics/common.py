"""
.. module:: soap.semantics.common
    :synopsis: Common definitions for semantics.
"""
import gmpy2


def precision_context(prec):
    """Withable context for changing precisions. Unifies how precisions can be
    changed.

    :param prec: The mantissa width.
    :type prec: int
    """
    # prec is the mantissa width
    # need to include the implicit integer bit for gmpy2
    prec += 1
    return gmpy2.local_context(gmpy2.ieee(128), precision=prec)
