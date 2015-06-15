import unittest

from soap.datatype import int_type, IntegerArrayType
from soap.expression import Expression, expression_factory, operators, Variable
from soap.parser import expr_parse
from soap.semantics import BoxState
from soap.semantics.linalg import IntegerIntervalArray
from soap.semantics.state.meta import MetaState
from soap.transformer import arithmetic, pattern
from soap.transformer.utils import parsings, reduce

Expression.__repr__ = lambda self: self.__str__()


class TestArithmeticEquivalence(unittest.TestCase):
    """
    Unit testing for :mod:`soap.transformer.arithmetic`.
    """
    def test_associativity(self):
        for e in ['(a + b) + c', '(b + a) + c', 'c + (a + b)', 'c + (b + a)']:
            f = pattern.transform(
                arithmetic.associativity_addition, expr_parse(e))
            self.assertIn(expr_parse('a + (b + c)'), f)
            self.assertIn(expr_parse('b + (a + c)'), f)
        for e in ['(a * b) * c', '(b * a) * c', 'c * (a * b)', 'c * (b * a)']:
            f = pattern.transform(
                arithmetic.associativity_multiplication, expr_parse(e))
            self.assertIn(expr_parse('a * (b * c)'), f)
            self.assertIn(expr_parse('b * (a * c)'), f)

    def test_distributivity_distribute(self):
        for e in ['(a + b) * c', '(b + a) * c', 'c * (a + b)', 'c * (b + a)']:
            f = pattern.transform(
                arithmetic.distributivity_distribute_multiplication,
                expr_parse(e))
            self.assertIn(expr_parse('a * c + b * c'), f)
        e = expr_parse('-(a + b)')
        f = pattern.transform(
            arithmetic.distributivity_distribute_unary_subtraction_addition, e)
        self.assertIn(expr_parse('-a - b'), f)

    def test_distributivity_collect(self):
        e = expr_parse('c * a + b * c')
        f = pattern.transform(
            arithmetic.distributivity_collect_multiplication, e)
        self.assertIn(expr_parse('(a + b) * c'), f)

    def test_negation(self):
        e = expr_parse('a - b')
        f = pattern.transform(arithmetic.negation, e)
        self.assertIn(expr_parse('a + -b'), f)

    def test_identity_reduction(self):
        e = expr_parse('0 + a')
        f = pattern.transform(arithmetic.identity_reduction_addition, e)
        self.assertIn(expr_parse('a'), f)
        e = expr_parse('1 * a')
        f = pattern.transform(arithmetic.identity_reduction_multiplication, e)
        self.assertIn(expr_parse('a'), f)
        e = expr_parse('a / 1')
        f = pattern.transform(arithmetic.identity_reduction_division, e)
        self.assertIn(expr_parse('a'), f)

    def test_double_negation_reduction(self):
        e = expr_parse('--a')
        f = pattern.transform(arithmetic.double_negation_reduction, e)
        self.assertIn(expr_parse('a'), f)

    def test_zero_reduction(self):
        e = expr_parse('a * 0')
        f = pattern.transform(arithmetic.zero_reduction_multiplication, e)
        self.assertIn(expr_parse('0'), f)
        e = expr_parse('0 / a')
        f = pattern.transform(arithmetic.zero_reduction_division, e)
        self.assertIn(expr_parse('0'), f)

    def test_constant_reduction(self):
        e = expr_parse('1 + 2')
        f = pattern.transform(arithmetic.constant_reduction, e)
        self.assertIn(expr_parse('3'), f)


class TestArithTreeTransformer(unittest.TestCase):
    """
    Unit testing for :class:`soap.transformer.arithmetic.ArithTreeTransformer`.
    """
    def test_parsings(self):
        e = expr_parse('a + b + c + d')
        f = parsings(e)
        g = {
            expr_parse('((a + b) + c) + d'),
            expr_parse('(a + (b + c)) + d'),
            expr_parse('(a + (b + d)) + c'),
            expr_parse('(a + b) + (c + d)'),
            expr_parse('(a + c) + (b + d)'),
            expr_parse('(b + (a + c)) + d'),
            expr_parse('(b + (a + d)) + c'),
            expr_parse('(b + c) + (a + d)'),
            expr_parse('a + ((b + c) + d)'),
            expr_parse('a + (b + (c + d))'),
            expr_parse('a + (c + (b + d))'),
            expr_parse('b + ((a + c) + d)'),
            expr_parse('b + ((a + d) + c)'),
            expr_parse('b + (a + (c + d))'),
            expr_parse('c + ((a + b) + d)'),
        }
        self.assertEqual(f, g)

    def test_reduction(self):
        e = {
            expr_parse('a + 1 * b'),
            expr_parse('a * 1 + b'),
            expr_parse('(a + 0) + b'),
        }
        f = reduce(e)
        g = {
            expr_parse('a + b')
        }
        self.assertEqual(f, g)


from soap.transformer.partition import partition, partition_optimize


class TestPartition(unittest.TestCase):
    def setUp(self):
        mat = IntegerIntervalArray([1, 2, 3, 4])
        self.x = Variable('x', int_type)
        self.y = Variable('y', int_type)
        self.z = Variable('z', IntegerArrayType([4]))
        self.state = BoxState({
            self.x: [1, 2],
            self.y: 3,
            self.z: mat,
        })

    def test_UpdateExpr(self):
        expr = expression_factory(
            operators.INDEX_UPDATE_OP,
            self.z, expression_factory(operators.SUBSCRIPT_OP, self.y), self.x)
        label, env = partition(expr, self.state)
        print(label)
        print(MetaState(env).format())

    def test_MetaState(self):
        from soap import parse, flow_to_meta_state
        flow = parse(
            """
            def main(real[30] a=[0.0, 1.0], real x=[0.0, 1.0]) {
                for (int i = 0; i < 10; i = i + 1) {
                    a[i] = x * i + x * i;
                }
                real z = a[0] + a[1];
                return z;
            }
            """)
        meta_state = flow_to_meta_state(flow)
        env = partition_optimize(
            meta_state, BoxState(flow.inputs), flow.outputs)
        print(MetaState(env).format())
