import collections

from soap.semantics.error import IntegerInterval, ErrorSemantics
from soap.semantics.linalg import IntegerIntervalArray, ErrorSemanticsArray


class TypeBase(object):
    """The base class of all data types.  """
    def __repr__(self):
        return '<{}>'.format(self)

    def __eq__(self, other):
        return self.__class__ == other.__class__

    def __hash__(self):
        return hash(self.__class__)


class AutoType(TypeBase):
    """Don't care type.  """
    def __str__(self):
        return 'auto'


class BoolType(TypeBase):
    """Boolean data type.  """
    def __str__(self):
        return 'bool'


class IntType(TypeBase):
    """Integer data type.  """
    def __str__(self):
        return 'int'


class FloatingPointType(TypeBase):
    """Floating-point data type.  """
    def __str__(self):
        return 'fp'


class FloatType(FloatingPointType):
    """Single-precision floating-point data type.  """
    def __str__(self):
        return 'float'


class DoubleType(FloatingPointType):
    """Double-precision floating-point data type.  """
    def __str__(self):
        return 'double'


class FunctionType(TypeBase):
    """Function data type.  """
    def __str__(self):
        return 'func'


auto_type = AutoType()
bool_type = BoolType()
int_type = IntType()
float_type = FloatType()
double_type = DoubleType()
function_type = FunctionType()


class ArrayType(TypeBase):
    num_type = None

    def __init__(self, shape):
        super().__init__()
        new_shape = []
        for s in shape:
            if isinstance(s, IntegerInterval):
                if s.min != s.max:
                    raise ValueError('Array size must be a constant.')
                s = int(s.min)
            new_shape.append(s)
        self.shape = tuple(new_shape)

    def __str__(self):
        return '{}[{}]'.format(
            self.num_type, ', '.join(str(d) for d in self.shape))

    def __eq__(self, other):
        return (
            self.__class__ == other.__class__ and
            self.num_type == other.num_type and
            self.shape == other.shape)

    def __hash__(self):
        return hash((self.__class__, self.num_type, self.shape))


class IntegerArrayType(ArrayType):
    num_type = int_type


class FloatArrayType(ArrayType):
    num_type = float_type


def type_of(value):
    if value is None:
        return
    if isinstance(value, IntegerInterval):
        return int_type
    if isinstance(value, ErrorSemantics):
        return float_type
    if isinstance(value, IntegerIntervalArray):
        return IntegerArrayType(value.shape)
    if isinstance(value, ErrorSemanticsArray):
        return FloatArrayType(value.shape)
    raise TypeError('Unrecognized type {}'.format(type(value)))


def type_cast(dtype, value=None, top=False, bottom=False):
    if dtype == int_type:
        return IntegerInterval(value, top=top, bottom=bottom)
    if dtype == float_type:
        return ErrorSemantics(value, top=top, bottom=bottom)
    if isinstance(dtype, IntegerArrayType):
        cls = IntegerIntervalArray
    elif isinstance(dtype, FloatArrayType):
        cls = ErrorSemanticsArray
    else:
        raise TypeError('Do not recognize type.')
    shape = dtype.shape
    if isinstance(dtype, ArrayType):
        if not isinstance(value, collections.Sequence):
            for dim in reversed(dtype.shape):
                value = [value] * dim
            return cls(_flat_items=value, _shape=shape, top=top, bottom=bottom)
    array = cls(value, _shape=shape, top=top, bottom=bottom)
    if shape is not None and dtype.shape != array.shape:
        raise ValueError(
            'Array shape is not the same as the shape specified by data type.')
    return array
