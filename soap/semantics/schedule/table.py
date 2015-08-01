from collections import namedtuple

from soap.datatype import int_type, float_type, ArrayType
from soap.context import context
from soap.expression import operators


DEVICE_LATENCY_TABLE = {
    ('Virtex7', 333): {
        int_type: {
            'comparison': 1,
            operators.UNARY_SUBTRACT_OP: 0,
            operators.ADD_OP: 1,
            operators.SUBTRACT_OP: 1,
            operators.MULTIPLY_OP: 7,
            operators.DIVIDE_OP: 36,
            operators.TERNARY_SELECT_OP: 0,
            operators.INDEX_ACCESS_OP: 2,
        },
        float_type: {
            'comparison': 3,
            'conversion': 8,
            operators.UNARY_SUBTRACT_OP: 0,
            operators.ADD_OP: 10,
            operators.SUBTRACT_OP: 10,
            operators.MULTIPLY_OP: 7,
            operators.DIVIDE_OP: 30,
            operators.EXPONENTIATE_OP: 20,
            operators.TERNARY_SELECT_OP: 0,
            operators.INDEX_ACCESS_OP: 2,
        },
        ArrayType: {
            operators.TERNARY_SELECT_OP: 0,
            operators.INDEX_UPDATE_OP: 1,
            operators.SUBSCRIPT_OP: 0,
        },
    },
}


NONPIPELINED_OPERATORS = {
    operators.FIXPOINT_OP,
}
PIPELINED_OPERATORS = set(operators.OPERATORS) - NONPIPELINED_OPERATORS
MAX_SHARE_COUNT = 128
MULTIPLEXER_SIZE_PER_INPUT = 10
SHARED_DATATYPE_OPERATORS = {
    (float_type, 'conversion'),
    (float_type, 'comparison'),
    (float_type, operators.ADD_OP),
    (float_type, operators.SUBTRACT_OP),
    (float_type, operators.MULTIPLY_OP),
    (float_type, operators.DIVIDE_OP),
}


class OperatorResourceTuple(namedtuple('Statistics', ['dsp', 'ff', 'lut'])):
    def __add__(self, other):
        dsp, ff, lut = [a + b for a, b in zip(self, other)]
        return self.__class__(dsp, ff, lut)
    __radd__ = __add__

    def __mul__(self, other):
        if not isinstance(other, (int, float)):
            raise TypeError(
                '{} can only be multiplied with a number.'
                .format(self.__class__.__name__))
        return self.__class__(
            other * self.dsp, other * self.ff, other * self.lut)
    __rmul__ = __mul__


s = OperatorResourceTuple


DEVICE_RESOURCE_TABLE = {
    'Virtex7': {
        int_type: {
            'comparison': s(0, 0, 39),
            operators.ADD_OP: s(0, 32, 32),
            operators.SUBTRACT_OP: s(0, 32, 32),
            operators.MULTIPLY_OP: s(4, 32, 32),
            operators.DIVIDE_OP: s(0, 2016, 2016),
            operators.UNARY_SUBTRACT_OP: s(0, 0, 1),
            operators.TERNARY_SELECT_OP: s(0, 32, 71),
            operators.FIXPOINT_OP: s(0, 0, 71),
            operators.BARRIER_OP: s(0, 0, 0),
            operators.INDEX_ACCESS_OP: s(0, 0, 0),
        },
        float_type: {
            'conversion': s(0, 128, 341),
            'comparison': s(0, 66, 72),
            operators.ADD_OP: s(2, 364, 238),  # full dsp
            operators.SUBTRACT_OP: s(2, 364, 238),  # full dsp
            operators.MULTIPLY_OP: s(3, 197, 123),  # max dsp
            operators.DIVIDE_OP: s(0, 1410, 867),
            operators.UNARY_SUBTRACT_OP: s(0, 0, 1),
            operators.EXPONENTIATE_OP: s(7, 483, 1053),  # full dsp
            operators.TERNARY_SELECT_OP: s(0, 0, 71),
            operators.FIXPOINT_OP: s(0, 0, 0),
            operators.BARRIER_OP: s(0, 0, 0),
            operators.INDEX_ACCESS_OP: s(0, 0, 0),
        },
        ArrayType: {
            operators.TERNARY_SELECT_OP: s(0, 32, 71),
            operators.INDEX_UPDATE_OP: s(0, 0, 0),
            operators.SUBSCRIPT_OP: s(0, 0, 0),
        }
    },
}


try:
    LATENCY_TABLE = DEVICE_LATENCY_TABLE[context.device, context.frequency]
    RESOURCE_TABLE = DEVICE_RESOURCE_TABLE[context.device]
except KeyError:
    raise KeyError(
        'Statistics for device {} and frequency {} MHz combination not found.'
        .format(context.device, context.frequency))
