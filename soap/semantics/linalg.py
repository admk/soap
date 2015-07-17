import collections
import functools
import itertools

from soap.lattice.base import join, Lattice
from soap.semantics.error import ErrorSemantics, FloatInterval, IntegerInterval


class MultiDimensionalArray(Lattice, collections.Sequence):
    __slots__ = ('_flat_items', 'scalar', 'shape', '_c_top', '_c_bottom')
    value_class = None

    def __init__(self, items=None, scalar=None, _flat_items=None,
                 _shape=None, bottom=False, top=False):
        super().__init__(bottom=bottom, top=top)
        self.shape = _shape
        if top or bottom:
            return
        self.scalar = scalar
        if scalar is None:
            self._init_flat_items(items, _flat_items, _shape)

    def is_scalar(self):
        return self.scalar is not None

    def _init_flat_items(self, items, _flat_items, _shape):
        def append_flat_items(flattened_flat_items, items):
            n = [len(items)]
            if not isinstance(items[0], (list, tuple)):
                flattened_flat_items += items
                return n
            first_len_list = None
            for each in items:
                each_len_list = append_flat_items(flattened_flat_items, each)
                if first_len_list is None:
                    first_len_list = each_len_list
                if each_len_list != first_len_list:
                    raise ValueError('Shape mismatch.')
            return n + first_len_list

        if _flat_items is not None:
            self.shape = _shape
            if not isinstance(_flat_items, tuple):
                _flat_items = tuple(_flat_items)
            self._flat_items = _flat_items
        else:
            flattened_flat_items = []
            shape = tuple(append_flat_items(flattened_flat_items, items))
            self.shape = _shape or shape
            self._flat_items = tuple(
                item if isinstance(item, self.value_class) else
                self.value_class(item) for item in flattened_flat_items)

        # set up shape_prod for index translation
        shape_prod = []
        prod = 1
        for size in reversed(self.shape):
            shape_prod.append(prod)
            prod *= size
        self._shape_prod = tuple(reversed(shape_prod))

    @property
    def size(self):
        return functools.reduce(lambda x, y: x * y, self.shape)

    def is_top(self):
        try:
            return self._c_top
        except AttributeError:
            pass
        if self.scalar is not None:
            top = self.scalar.is_top()
        else:
            top = all(i.is_top() for i in self._flat_items)
        self._c_top = top
        return top

    def is_bottom(self):
        try:
            return self._c_top
        except AttributeError:
            pass
        if self.scalar is not None:
            bot = self.scalar.is_bottom()
        else:
            bot = all(i.is_bottom() for i in self._flat_items)
        self._c_bottom = bot
        return bot

    def join(self, other):
        if self.shape != other.shape:
            raise ValueError('Shape mismatch.')
        if self.scalar is not None:
            return self.__class__(
                scalar=self.scalar.join(other.scalar), _shape=self.shape)
        items = tuple(
            x.join(y) for x, y in zip(self._flat_items, other._flat_items))
        return self.__class__(_flat_items=items, _shape=self.shape)

    def meet(self, other):
        if self.shape != other.shape:
            raise ValueError('Shape mismatch.')
        if self.scalar is not None:
            return self.__class__(
                scalar=self.scalar.meet(other.scalar), _shape=self.shape)
        items = tuple(
            x.meet(y) for x, y in zip(self._flat_items, other._flat_items))
        return self.__class__(_flat_items=items, _shape=self.shape)

    def _to_flat_index(self, index):
        return sum((i * p for i, p in zip(index, self._shape_prod)))

    def to_nested_list(self):
        items = self._flat_items
        # woah?
        for s in reversed(self.shape[1:]):
            items = [list(items[i:i + s]) for i in range(0, len(items), s)]
        return items

    def transpose(self):
        if len(self.shape) != 2:
            raise TypeError('The array being transposed is not a matrix.')
        raise NotImplementedError

    @property
    def T(self):
        return self.transpose()

    def _normalize_index(self, index):
        if not isinstance(index, collections.Sequence):
            index = [index]

        index_iterer = []
        for (i, s) in zip(index, self.shape):
            if isinstance(i, int):
                if not (0 <= i < s):
                    raise IndexError('Index out of range')
                index_iterer.append([i])
            elif isinstance(i, (list, IntegerInterval)):
                min_val, max_val = i
                if not (0 <= min_val <= max_val < s):
                    raise IndexError(
                        'Index interval {} out of range {}'.format(i, s))
                index_iterer.append(range(min_val, max_val + 1))
            else:
                raise TypeError(
                    'Index must be an integer or an IntegerInterval.')
        return tuple(itertools.product(*index_iterer))

    def __getitem__(self, index):
        top = self.is_top()
        bottom = self.is_bottom()
        if top or bottom:
            return self.value_class(top=top, bottom=bottom)

        if self.scalar is not None:
            return self.scalar

        # fast path for one-dimensional arrays
        if isinstance(index, int):
            return self._flat_items[index]

        items = []
        for i in self._normalize_index(index):
            item = self._flat_items[self._to_flat_index(i)]
            items.append(item)
        return join(items)

    def update(self, index, value):
        top = self.is_top()
        bottom = self.is_bottom()
        shape = self.shape

        if self.scalar is not None:
            if top or bottom:
                return self
            value = value.join(self.scalar)
            return self.__class__(scalar=value, _shape=shape)

        if top or bottom:
            # extrapolate items in the matrix
            other_value = self.value_class(top=top, bottom=bottom)
            items = [other_value] * self.size
        else:
            cls = self.value_class
            if not isinstance(value, cls):
                value = cls(value)
            items = list(self._flat_items)

        # fast path for one-dimensional arrays
        if isinstance(index, int):
            items[index] = value
            return self.__class__(_flat_items=items, _shape=shape)

        indices = self._normalize_index(index)

        # only a specific item is changed
        if len(indices) == 1:
            items[self._to_flat_index(indices[0])] = value
            return self.__class__(_flat_items=items, _shape=shape)

        for index in indices:
            index = self._to_flat_index(index)
            items[index] |= value

        return self.__class__(_flat_items=items, _shape=shape)

    def le(self, other):
        if self.shape != other.shape:
            raise ValueError('Cannot compare arrays with different shapes.')
        if self.scalar is not None:
            return self.scalar.le(other.scalar)
        return all(
            x.le(y) for x, y in zip(self._flat_items, other._flat_items))

    def widen(self, other):
        if self.scalar is not None:
            return self.__class__(
                scalar=self.scalar.widen(other.scalar), _shape=self.shape)
        items = [
            x.widen(y) for x, y in zip(self._flat_items, other._flat_items)]
        return self.__class__(_flat_items=items, _shape=self.shape)

    def __len__(self):
        return self.size()

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        # FIXME workaround for a weird bug about top and bottom values
        if (self.bottom and other.bottom) or (self.top and other.top):
            return True
        if self.shape != other.shape:
            return False
        if self.scalar is not None:
            return self.scalar == other.scalar
        return self._flat_items == other._flat_items

    def __hash__(self):
        if self.scalar is not None:
            hash_val = hash((self.scalar, self.shape))
        else:
            hash_val = hash((self._flat_items, self.shape))
        self._hash = hash_val
        return hash_val

    def _format_matrix(self):
        items = []
        widths = [0] * self.shape[1]
        for row in self.to_nested_list():
            new_row = []
            for idx, val in enumerate(row):
                val = str(val)
                new_row.append(val)
                widths[idx] = max(widths[idx], len(val))
            items.append(new_row)
        if len(widths) == 1:
            return '[{}]'.format(
                '\n '.join(
                    '{val:^{len}}'.format(val=row[0], len=widths[0])
                    for row in items))
        return '[{}]'.format(
            '\n '.join(
                '[{}]'.format(' '.join(
                    '{val:^{len}}'.format(val=v, len=widths[i])
                    for i, v in enumerate(row)))
                for row in items))

    def __str__(self):
        if self.scalar is not None:
            shape = 'x'.join(str(s) for s in self.shape)
            return '[{}: {}]'.format(shape, self.scalar)
        if len(self.shape) == 1:
            return '[{}]'.format(', '.join(str(v) for v in self._flat_items))
        if len(self.shape) == 2:
            return self._format_matrix()
        return str(self.to_nested_list())

    def __repr__(self):
        if self.scalar is not None:
            return '{}(scalar={!r}, _shape={!r})'.format(
                self.__class__.__name__, self.scalar, self.shape)
        return '{}({!r})'.format(self.__class__.__name__, self._flat_items)


class IntegerIntervalArray(MultiDimensionalArray):
    value_class = IntegerInterval


class FloatIntervalArray(MultiDimensionalArray):
    value_class = FloatInterval


class ErrorSemanticsArray(MultiDimensionalArray):
    value_class = ErrorSemantics
