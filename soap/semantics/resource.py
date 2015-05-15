from collections import namedtuple

from soap.common import cached
from soap.context import context
from soap.expression import operators, is_expression, External, FixExpr
from soap.semantics.common import is_numeral
from soap.semantics.error import ErrorSemantics, IntegerInterval
from soap.semantics.label import Label


class OperatorResourceTuple(namedtuple('Statistics', ['dsp', 'ff', 'lut'])):
    def __add__(self, other):
        dsp, ff, lut = [a + b for a, b in zip(self, other)]
        return self.__class__(dsp, ff, lut)
s = OperatorResourceTuple


resource_table = {
    'stratix4': {
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
            operators.SUBTRACT_OP: s(0, 0, 0),
            operators.INDEX_ACCESS_OP: s(0, 0, 0),
            operators.INDEX_UPDATE_OP: s(0, 0, 0),
        },
        'single': {
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
            operators.SUBTRACT_OP: s(0, 0, 0),
            operators.INDEX_ACCESS_OP: s(0, 0, 0),
            operators.INDEX_UPDATE_OP: s(0, 0, 0),
        },
        'double': {},
    },
    'virtex7': {
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
        },
        'single': {
            'conversion': s(0, 128, 341),
            'comparison': s(0, 66, 72),
            operators.ADD_OP: s(2, 227, 214),
            operators.SUBTRACT_OP: s(2, 227, 214),
            operators.MULTIPLY_OP: s(3, 128, 135),
            operators.DIVIDE_OP: s(0, 363, 802),
            operators.UNARY_SUBTRACT_OP: s(0, 0, 37),
            operators.TERNARY_SELECT_OP: s(0, 0, 71),
            operators.FIXPOINT_OP: s(0, 0, 0),
            operators.BARRIER_OP: s(0, 0, 0),
        },
        'double': {},
    },
}


def _accumulate_count(env, integer_table, float_table):
    stat = s(0, 0, 0)
    conversion_set = set()
    for label, expr in env.items():
        if is_expression(expr) and not isinstance(expr, External):
            op = expr.op
            if op in operators.COMPARISON_OPERATORS:
                op = 'comparison'
            if isinstance(label, Label):
                datatype = type(label.bound)
            else:
                datatype = None
            if datatype is IntegerInterval:
                stat += integer_table[op]
            elif datatype is ErrorSemantics:
                for arg in expr.args:
                    if not isinstance(arg, Label):
                        continue
                    if not isinstance(arg.bound, IntegerInterval):
                        continue
                    if is_numeral(env[arg]):
                        continue
                    conversion_set.add(arg)
                stat += float_table[op]
        if isinstance(expr, FixExpr):
            for e in (expr.bool_expr[1], expr.loop_state, expr.init_state):
                stat += _accumulate_count(e, integer_table, float_table)
    dsp, ff, lut = float_table['conversion']
    no_conv = len(conversion_set)
    stat += s(no_conv * dsp, no_conv * ff, no_conv * lut)
    return stat


@cached
def resource_count(labsem):
    table = resource_table[context.device]
    integer_table = table['integer']
    float_table = table[{23: 'single', 52: 'double'}[context.precision]]
    return _accumulate_count(labsem.env, integer_table, float_table)
