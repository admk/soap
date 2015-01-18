import itertools
import unittest

from soap.semantics.error import IntegerInterval
from soap.semantics.linalg import IntegerIntervalArray as IntArray


class TestIntArray(unittest.TestCase):
    def _list_elements_to_interval(self, values):
        return [[IntegerInterval(e) for e in l] for l in values]

    def setUp(self):
        self.vector_values = [1, 2, 3]
        self.vector = IntArray(self.vector_values)
        self.matrix_values = self._list_elements_to_interval([
            [[1, 5], [2, 6], [3, 7]],
            [[4, 8], [5, 9], [6, 9]],
            [[7, 9], [8, 9], [9, 9]]])
        self.matrix = IntArray(self.matrix_values)

    def test_matrix_shape(self):
        self.assertEqual(self.matrix.shape, (3, 3))

    def test_matrix_content(self):
        intervals = [IntegerInterval(v) for v in self.vector_values]
        self.assertListEqual(intervals, list(self.vector))
        x_shape, y_shape = self.matrix.shape
        for x, y in itertools.product(range(x_shape), range(y_shape)):
            val = IntegerInterval(self.matrix_values[x][y])
            self.assertEqual(val, self.matrix[x, y])

    def test_matrix_getter(self):
        self.assertEqual(self.matrix[1, 2], IntegerInterval([6, 9]))
        self.assertEqual(self.matrix[[0, 1], 1], IntegerInterval([2, 9]))

    def test_matrix_update(self):
        mat = self.matrix.update((1, 2), 1)
        self.assertEqual(mat[1, 2], IntegerInterval(1))
        mat = self.matrix.update(([1, 2], 1), 1)
        val = IntegerInterval([1, 9])
        self.assertEqual(mat[1, 1], val)
        self.assertEqual(mat[2, 1], val)

    def test_join_and_meet(self):
        other_matrix = IntArray(
            [[9, 8, 7],
             [6, 5, 4],
             [3, 2, 1]])
        join_test_matrix = IntArray(self._list_elements_to_interval(
            [[[1, 9], [2, 8], [3, 7]],
             [[4, 8], [5, 9], [4, 9]],
             [[3, 9], [2, 9], [1, 9]]]))
        self.assertEqual(self.matrix | other_matrix, join_test_matrix)
        bot = IntegerInterval(bottom=True)
        meet_test_matrix = IntArray(
            [[bot, bot, 7],
             [6, 5, bot],
             [bot, bot, bot]])
        self.assertEqual(self.matrix & other_matrix, meet_test_matrix)

    def test_to_nested_list(self):
        nested_list = self.matrix.to_nested_list()
        self.assertEqual(nested_list, self.matrix_values)

    def test_transpose(self):
        return NotImplemented
        matrix = IntArray([[1, 2], [3, 4], [5, 6]])
        transpose_test_matrix = IntArray([[1, 3, 5], [2, 4, 6]])
        self.assertEqual(matrix.transpose(), transpose_test_matrix)
