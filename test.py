from pprint import *
from soap import *
from soap.semantics.state.fusion import *
from soap.program.generator import *
from soap.program.graph import *

p = """
if a < 0:
    if b < 0:
        x = x + 1
    else:
        x = x + 2
if b < 0:
    if a < 0:
        y = 4
    else:
        y = 5
"""
print(flow(p).format())

s = flow_to_meta_state(p)
pprint('metasemantics')
pprint(s)

m = s.label()[1]
pprint('label')
pprint(m)

v = [expr('x'), expr('y')]

n = fusion(m, v)
pprint('merge')
pprint(n)

pprint('generate')
print(generate(n, v).format())
