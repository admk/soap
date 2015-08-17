import unittest

from soap.datatype import int_type, IntegerArrayType
from soap.expression.fixpoint import FixExpr
from soap.expression.linalg import AccessExpr, UpdateExpr
from soap.expression.variable import Variable
from soap.parser import stmt_parse, expr_parse
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
        self.stmt_parse = lambda prog: stmt_parse(prog, self.decl)

    def test_visit_AssignFlow(self):
        flow = self.stmt_parse('z = x * y;')
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
        flow = self.stmt_parse('if (x < z) {x = x + 1;} else {x = x - 1;}')
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

    def _loop_compare_state(self):
        init_state = MetaState({
            self.x: self.x,
            self.z: self.z,
        })
        fix_loop_state = MetaState({
            self.x: self.expr_parse('x + 1'),
            self.z: self.z,
        })

        fix_expr_x = FixExpr(
            self.expr_parse('x < z'), fix_loop_state, self.x, init_state)

        init_state = init_state.immu_update(self.y, self.y)
        fix_loop_state = fix_loop_state.immu_update(
            self.y, self.expr_parse('y * x'))

        fix_expr_y = FixExpr(
            self.expr_parse('x < z'), fix_loop_state, self.y, init_state)

        fix_compare_state = MetaState({
            self.x: fix_expr_x,
            self.y: fix_expr_y,
            self.z: self.z,
        })
        return fix_compare_state

    def test_visit_WhileFlow(self):
        flow = self.stmt_parse('while (x < z) {y = y * x; x = x + 1;}')
        state = MetaState({
            self.x: self.x,
            self.y: self.y,
            self.z: self.z,
        })
        state = state.visit_WhileFlow(flow)
        self.assertEqual(state, self._loop_compare_state())

    def test_visit_ForFlow(self):
        flow = self.stmt_parse('for (x = x; x < z; x = x + 1) {y = y * x;}')
        state = MetaState({
            self.x: self.x,
            self.y: self.y,
            self.z: self.z,
        })
        state = state.visit_ForFlow(flow)
        self.assertEqual(state, self._loop_compare_state())

    def test_visit_CompositionalFlow(self):
        flow = self.stmt_parse('x = x + 1; x = x * 2;')
        state = MetaState({self.x: self.x}).visit_CompositionalFlow(flow)
        compare_state = MetaState({self.x: self.expr_parse('(x + 1) * 2')})
        self.assertEqual(state, compare_state)

    def test_access_expr(self):
        flow = self.stmt_parse('x = a[y];')
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
        flow = self.stmt_parse('x = b[y][z];')
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
        flow = self.stmt_parse('a[x] = 1;')
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
        flow = self.stmt_parse('b[x][y] = 1;')
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
