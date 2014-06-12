import functools
from pprint import pprint
import unittest

from soap.expression import parse, OutputVariableTuple
from soap.semantics import flow_to_meta_state
from soap.semantics.state.fusion import fusion

from examples import test_programs


class TestFusion(unittest.TestCase):

    def check(self, case):
        def find_output_variable_tuple(env):
            for k, v in env.items():
                if isinstance(k, OutputVariableTuple):
                    yield k
        state = flow_to_meta_state(case['program'])
        new_state = fusion(state.label()[1], case['out_vars'])
        pprint(dict(new_state))
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
