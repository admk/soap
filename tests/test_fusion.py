import unittest

from soap.expression import OutputVariableTuple
from soap.parser import parse
from soap.semantics import BoxState, flow_to_meta_state
from soap.semantics.functions.label import _label
from soap.semantics.state.fusion import fusion

from examples import test_programs


class TestFusion(unittest.TestCase):

    def check(self, case):
        def find_output_variable_tuple(env):
            for k, v in env.items():
                if isinstance(k, OutputVariableTuple):
                    yield k
        flow = parse(case['program'])
        state = flow_to_meta_state(flow)
        label = _label(state, BoxState(bottom=True))[1]
        new_state = fusion(label, flow.outputs)
        out_vars = list(find_output_variable_tuple(new_state))
        fusion_count = case['fusion_count']
        self.assertEqual(len(out_vars), fusion_count)
        if fusion_count:
            self.assertEqual(len(out_vars.pop()), case['fusion_vartup_len'])

    def test_if(self):
        self.check(test_programs['if'])

    def test_while(self):
        self.check(test_programs['while'])

    def test_if_fusion(self):
        self.check(test_programs['if_fusion'])

    def test_while_fusion(self):
        self.check(test_programs['while_fusion'])

    def test_nested_if(self):
        self.check(test_programs['nested_if'])

    def test_nested_while(self):
        self.check(test_programs['nested_while'])
