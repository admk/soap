import collections

from soap.lattice.base import Lattice
from soap.semantics.error import ErrorSemantics, FloatInterval, IntegerInterval


class Matrix(Lattice, collections.Sequence):
    __slots__ = ('_items', )
    value_class = None

    def __init__(self, items=None, bottom=False, top=False):
        super().__init__(bottom=bottom, top=top)
        if top or bottom:
            return
        self._set_items(items)

    def is_top(self):
        return False

    def is_bottom(self):
        return False

    def join(self, other):
        new_items = []
        for self_row, other_row in zip(self, other):
            row = [x.join(y) for x, y in zip(self_row, other_row)]
            new_items.append(row)
        return self.__class__(new_items)

    def meet(self, other):
        new_items = []
        for self_row, other_row in zip(self, other):
            row = [x.meet(y) for x, y in zip(self_row, other_row)]
            new_items.append(row)
        return self.__class__(new_items)

    def _set_items(self, items):
        cls = self.value_class
        new_items = []
        shape = None
        for row in items:
            if not isinstance(row, collections.Sequence):
                row = (row, )
            row = tuple(cls(item) for item in row)
            if shape is None:
                shape = len(row)
            elif shape != len(row):
                raise ValueError('Row shape mismatch.')
            new_items.append(row)
        self._items = tuple(new_items)

    def __getitem__(self, index):
        top = self.is_top()
        bottom = self.is_bottom()
        if isinstance(index, int):
            if top or bottom:
                return self.value_class(top=top, bottom=bottom)
            row = self._items[index]
            if len(row) == 1:
                return row[0]
            else:
                return self.__class__([row])
        if isinstance(index, slice):
            if top or bottom:
                return self.__class__(top=top, bottom=bottom)
            return self.__class__(self._items[index])
        if isinstance(index, tuple):
            is_slice = any(isinstance(i, slice) for i in index)
            if top or bottom:
                if is_slice:
                    return self.__class__(top=top, bottom=bottom)
                else:
                    return self.value_class(top=top, bottom=bottom)
            row_index, col_index = index
            if not is_slice:
                return self._items[row_index][col_index]
            rows = self._items[row_index]
            if not isinstance(row_index, slice):
                rows = [rows]
            rows = tuple(row[col_index] for row in rows)
            return self.__class__(rows)
        raise IndexError('Do not know how to get item with index {}'
                         .format(index))

    @property
    def shape(self):
        return (len(self._items), len(self._items[0]))

    def __len__(self):
        return len(self._items)

    def __eq__(self, other):
        return self._items == other._items

    def __hash__(self):
        hash_val = self._hash = hash(self._items)
        return hash_val

    def __str__(self):
        items = []
        widths = [0] * self.shape[1]
        for row in self._items:
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

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self._items)


class IntegerIntervalMatrix(Matrix):
    value_class = IntegerInterval


class FloatIntervalMatrix(Matrix):
    value_class = FloatInterval


class ErrorSemanticsMatrix(Matrix):
    value_class = ErrorSemantics
