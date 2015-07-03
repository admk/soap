import unittest

from soap.context import context
from soap.parser import parse
from soap.semantics import BoxState, flow_to_meta_state
from soap.transformer.partition import partition_optimize


class TestPartition(unittest.TestCase):
    def setUp(self):
        context.take_snapshot()
        context.unroll_depth = 0
        flow = parse(
            """
            def main(real[20] a=[0.0, 1.0], real x=[0.0, 1.0]) {
                for (int i = 5; i < 20; i = i + 1) {
                    a[i] = (a[i - 1] + a[i - 2] + a[i - 3]) / 3;
                }
                return a;
            }
            """)
        self.flow = flow
        self.output = flow.outputs[0]
        self.meta_state = flow_to_meta_state(flow)
        self.state = BoxState(flow.inputs)

    def tearDown(self):
        context.restore_snapshot()

    def test_generate(self):
        alg = lambda expr, state, _: {expr}
        results = partition_optimize(
            self.meta_state, self.state, [self.output], optimize_algorithm=alg)

        self.assertEqual(len(results), 1)
        compare_meta_state = results.pop().expression
        self.assertEqual(
            self.meta_state[self.output], compare_meta_state[self.output])

    def test_optimize(self):
        with context.local(unroll_depth=1):
            env_list = partition_optimize(
                self.meta_state, self.state, [self.output])
            self.assertGreater(len(env_list), 1)
