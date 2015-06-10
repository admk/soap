from collections import namedtuple

from soap.common.base import dict_merge
from soap.context import context
from soap.expression import operators


DEVICE_LATENCY_TABLE = {
    ('Virtex7', 100): {
        'integer': {
            'comparison': 1,
            operators.UNARY_SUBTRACT_OP: 0,
            operators.ADD_OP: 1,
            operators.SUBTRACT_OP: 1,
            operators.MULTIPLY_OP: 1,
            operators.INDEX_ACCESS_OP: 1,
        },
        'float': {
            'comparison': 4,
            operators.UNARY_SUBTRACT_OP: 0,
            operators.ADD_OP: 4,
            operators.SUBTRACT_OP: 4,
            operators.MULTIPLY_OP: 3,
            operators.DIVIDE_OP: 8,
            operators.EXPONENTIATE_OP: 12,
            operators.INDEX_ACCESS_OP: 2,
        },
        'array': {
            operators.INDEX_UPDATE_OP: 1,
            operators.SUBSCRIPT_OP: 0,
        },
    },
}
DEVICE_LOOP_LATENCY_TABLE = {
    ('Virtex7', 100): {
        'float': {
            'comparison': 3,
            operators.ADD_OP: 3,
            operators.SUBTRACT_OP: 3,
            operators.MULTIPLY_OP: 2,
            operators.DIVIDE_OP: 7,
            operators.EXPONENTIATE_OP: 11,
            operators.INDEX_ACCESS_OP: 1,
        },
    },
}
DEVICE_LOOP_LATENCY_TABLE = dict_merge(
    DEVICE_LOOP_LATENCY_TABLE, DEVICE_LATENCY_TABLE)


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
    'Stratix4': {
        'integer': {
            'comparison': s(0, 65, 35),
            operators.ADD_OP: s(0, 96, 32),
            operators.SUBTRACT_OP: s(0, 96, 32),
            operators.MULTIPLY_OP: s(4, 96, 0),
            operators.DIVIDE_OP: s(0, 96, 1247),
            operators.UNARY_SUBTRACT_OP: s(0, 96, 32),
            operators.TERNARY_SELECT_OP: s(0, 96, 32),
            operators.FIXPOINT_OP: s(0, 96, 32),
            operators.BARRIER_OP: s(0, 0, 0),
            operators.INDEX_ACCESS_OP: s(0, 0, 0),
        },
        'float': {
            'conversion': s(0, 211, 186),
            'comparison': s(0, 33, 68),
            operators.ADD_OP: s(0, 540, 505),
            operators.SUBTRACT_OP: s(0, 540, 505),
            operators.MULTIPLY_OP: s(4, 222, 141),
            operators.DIVIDE_OP: s(0, 2788, 3198),
            operators.UNARY_SUBTRACT_OP: s(0, 0, 1),
            operators.TERNARY_SELECT_OP: s(0, 96, 32),
            operators.FIXPOINT_OP: s(0, 96, 32),
            operators.BARRIER_OP: s(0, 0, 0),
            operators.INDEX_ACCESS_OP: s(0, 0, 0),
        },
        'array': {
            operators.INDEX_UPDATE_OP: s(0, 0, 0),
            operators.SUBSCRIPT_OP: s(0, 0, 0),
        }
    },
    'Virtex7': {
        'integer': {
            'comparison': s(0, 0, 39),
            operators.ADD_OP: s(0, 0, 32),
            operators.SUBTRACT_OP: s(0, 0, 32),
            operators.MULTIPLY_OP: s(4, 45, 21),
            operators.DIVIDE_OP: s(0, 1712, 1779),
            operators.UNARY_SUBTRACT_OP: s(0, 0, 32),
            operators.TERNARY_SELECT_OP: s(0, 0, 71),
            operators.FIXPOINT_OP: s(0, 0, 71),
            operators.BARRIER_OP: s(0, 0, 0),
            operators.INDEX_ACCESS_OP: s(0, 0, 0),
        },
        'float': {
            'conversion': s(0, 128, 341),
            'comparison': s(0, 66, 72),
            operators.ADD_OP: s(2, 227, 214),  # full dsp
            operators.SUBTRACT_OP: s(2, 227, 214),  # full dsp
            operators.MULTIPLY_OP: s(3, 128, 135),  # max dsp
            operators.DIVIDE_OP: s(0, 363, 802),
            operators.UNARY_SUBTRACT_OP: s(0, 0, 37),
            operators.EXPONENTIATE_OP: s(26, 2935, 3787),
            operators.TERNARY_SELECT_OP: s(0, 0, 71),
            operators.FIXPOINT_OP: s(0, 0, 0),
            operators.BARRIER_OP: s(0, 0, 0),
            operators.INDEX_ACCESS_OP: s(0, 0, 0),
        },
        'array': {
            operators.INDEX_UPDATE_OP: s(0, 0, 0),
            operators.SUBSCRIPT_OP: s(0, 0, 0),
        }
    },
}


try:
    LATENCY_TABLE = DEVICE_LATENCY_TABLE[context.device, context.frequency]
    LOOP_LATENCY_TABLE = \
        DEVICE_LOOP_LATENCY_TABLE[context.device, context.frequency]
    RESOURCE_TABLE = DEVICE_RESOURCE_TABLE[context.device]
except KeyError:
    raise KeyError(
        'Statistics for device {} and frequency {} MHz combination not found.'
        .format(context.device, context.frequency))
