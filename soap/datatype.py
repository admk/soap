class TypeBase(object):
    """The base class of all data types.  """
    def __eq__(self, other):
        return self.__class__ == other.__class__

    def __hash__(self):
        return hash(self.__class__)


class IntegerType(TypeBase):
    """Integer data type.  """
    def __str__(self):
        return 'int'


class RealType(TypeBase):
    """Real data type.  """
    def __str__(self):
        return 'real'


int_type = IntegerType()
real_type = RealType()


class ArrayType(TypeBase):
    num_type = None

    def __init__(self, dim):
        super().__init__()
        self.dim = tuple(dim)

    def __str__(self):
        return '{}[{}]'.format(self.num_type, ', '.join(self.dim))

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.dim == other.dim

    def __hash__(self):
        return hash(self.__class__, self.dim)


class IntegerArrayType(ArrayType):
    num_type = int_type


class RealArrayType(ArrayType):
    num_type = real_type
