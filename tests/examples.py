from akpytemp.utils import code_gobble

from soap.expression import Variable
from soap.semantics import BoxState


test_programs = {
    'if': {
        'program': code_gobble(
            """
            if x < n:
                x = x + 1
            else:
                x = x - 1
            """),
        'fusion_count': 0,
        'fusion_vartup_len': 0,
        'out_vars': [Variable('x')],
        'inputs': BoxState(x=0, n=1),
    },
    'while': {
        'program': code_gobble(
            """
            while x < n:
                x = x + 1
            """),
        'fusion_count': 0,
        'fusion_vartup_len': 0,
        'out_vars': [Variable('x')],
        'inputs': BoxState(x=0, n=5),
    },
    'if_fusion': {
        'program': code_gobble(
            """
            if a < 1:
                x = x + 1
            if a < 1:
                y = y - 1
            """),
        'fusion_count': 1,
        'fusion_vartup_len': 2,
        'out_vars': [Variable('x'), Variable('y')],
        'inputs': BoxState(a=0, x=0, y=0),
    },
    'while_fusion': {
        'program': code_gobble(
            """
            k = x
            while x < n:
                x = x + 1
            x = k
            while x < n:
                y = y * x
                x = x + 1
            """),
        'fusion_count': 1,
        'fusion_vartup_len': 2,
        'out_vars': [Variable('x'), Variable('y')],
        'inputs': BoxState(x=0, y=1, n=5),
    },
    'nested_if': {
        'program': code_gobble(
            """
            if a < 0:
                if b < 0:
                    x = x + 1
            if b < 0:
                if a < 0:
                    y = y - 1
            """),
        'fusion_count': 1,
        'fusion_vartup_len': 2,
        'out_vars': [Variable('x'), Variable('y')],
        'inputs': BoxState(a=-1, b=-1, x=0, y=0),
    },
    'nested_while': {
        'program': code_gobble(
            """
            while x < n:
                x = x + 1
                while y < x:
                    y = y + 1
                x = x + y
            """),
        'fusion_count': 1,
        'fusion_vartup_len': 2,
        'out_vars': [Variable('x'), Variable('y')],
        'inputs': BoxState(x=1, y=0, n=5),
    },
}
