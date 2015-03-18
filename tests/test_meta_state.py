import unittest

from soap.datatype import int_type, IntegerArrayType
from soap.expression.fixpoint import FixExpr
from soap.expression.linalg import AccessExpr, UpdateExpr
from soap.expression.variable import Variable
from soap.parser.program import parse, expr_parse
from soap.semantics.state.meta import MetaState


class TestMetaState(unittest.TestCase):
    def setUp(self):
        array_type = IntegerArrayType([3])
        multi_array_type = IntegerArrayType([2, 3])
        self.decl = {
            'x': int_type, 'y': int_type, 'z': int_type,
            'a': array_type, 'b': multi_array_type,
        }
        self.x = Variable('x', int_type)
        self.y = Variable('y', int_type)
        self.z = Variable('z', int_type)
        self.a = Variable('a', array_type)
        self.b = Variable('b', multi_array_type)
        self.expr_parse = lambda expr: expr_parse(expr, self.decl)
        self.parse = lambda prog: parse(prog, self.decl)

    def test_visit_IdentityFlow(self):
        state = MetaState({self.x: self.x})
        compare_state = state.visit_IdentityFlow(parse('skip;'))
        self.assertEqual(state, compare_state)

    def test_visit_AssignFlow(self):
        flow = self.parse('z = x * y;')
        state = MetaState({
            self.x: self.expr_parse('x + 1'),
            self.y: self.expr_parse('y + 2'),
        })
        state = state.visit_AssignFlow(flow)
        compare_state = MetaState({
            self.x: self.expr_parse('x + 1'),
            self.y: self.expr_parse('y + 2'),
            self.z: self.expr_parse('(x + 1) * (y + 2)'),
        })
        self.assertEqual(state, compare_state)

    def test_visit_IfFlow(self):
        flow = self.parse('if (x < z) {x = x + 1;} else {x = x - 1;};')
        state = MetaState({
            self.x: self.y,
            self.z: self.z,
        })
        state = state.visit_IfFlow(flow)
        compare_state = MetaState({
            self.x: self.expr_parse('y < z ? y + 1 : y - 1'),
            self.z: self.z,
        })
        self.assertEqual(state, compare_state)

    def test_visit_WhileFlow(self):
        flow = self.parse('while (x < z) {x = x + 1;};')
        state = MetaState({
            self.x: self.x,
            self.y: self.y,
            self.z: self.z,
        })
        state = state.visit_WhileFlow(flow)
        init_state = MetaState({
            self.x: self.x,
            self.z: self.z,
        })
        loop_state = MetaState({
            self.x: self.expr_parse('x + 1'),
            self.z: self.z,
        })
        fix_expr = FixExpr(
            self.expr_parse('x < z'), loop_state, self.x, init_state)
        compare_state = MetaState({
            self.x: fix_expr,
            self.y: self.y,
            self.z: self.z,
        })
        self.assertEqual(state, compare_state)

    def test_visit_CompositionalFlow(self):
        flow = self.parse('x = x + 1; x = x * 2;')
        state = MetaState({self.x: self.x}).visit_CompositionalFlow(flow)
        compare_state = MetaState({self.x: self.expr_parse('(x + 1) * 2')})
        self.assertEqual(state, compare_state)

    def test_access_expr(self):
        flow = self.parse('x = a[y];')
        state = MetaState({
            self.a: self.a,
            self.x: self.x,
            self.y: self.y,
        })
        state = state.visit_AssignFlow(flow)
        compare_state = MetaState({
            self.a: self.a,
            self.x: AccessExpr(self.a, [self.y]),
            self.y: self.y,
        })
        self.assertEqual(state, compare_state)

    def test_access_expr_multi(self):
        flow = self.parse('x = b[y, z];')
        state = MetaState({
            self.b: self.b,
            self.x: self.x,
            self.y: self.y,
            self.z: self.z,
        })
        state = state.visit_AssignFlow(flow)
        subs = [self.y, self.z]
        compare_state = MetaState({
            self.b: self.b,
            self.x: AccessExpr(self.b, subs),
            self.y: self.y,
            self.z: self.z,
        })
        self.assertEqual(state, compare_state)

    def test_update_expr(self):
        flow = self.parse('a[x] = 1;')
        state = MetaState({
            self.a: self.a,
            self.x: self.y,
        })
        state = state.visit_AssignFlow(flow)
        compare_state = MetaState({
            self.a: UpdateExpr(self.a, [self.y], self.expr_parse('1')),
            self.x: self.y,
        })
        self.assertEqual(state, compare_state)

    def test_update_expr_multi(self):
        flow = self.parse('b[x, y] = 1;')
        state = MetaState({
            self.b: self.b,
            self.x: self.y,
            self.y: self.z,
            self.z: self.x,
        })
        state = state.visit_AssignFlow(flow)
        subs = [self.y, self.z]
        compare_state = MetaState({
            self.b: UpdateExpr(self.b, subs, self.expr_parse('1')),
            self.x: self.y,
            self.y: self.z,
            self.z: self.x,
        })
        self.assertEqual(state, compare_state)
