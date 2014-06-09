from pprint import *
from soap import *
from soap.label import *
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
q = """
n = n + 1
while x < n:
    x = x + 1
    y = y * x
"""
v = [expr('x'), expr('y')]

print(flow(p).format())

s = flow_to_meta_state(p)
pprint('metasemantics')
pprint(dict(s))

c = LabelContext('1', out_vars=v)
m = s.label(c)[1]
pprint('label')
pprint(dict(m))

pprint('generate')
print(generate(m, v).format())
