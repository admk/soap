from pprint import *
from soap import *
from soap.program.generator import *
from soap.program.graph import *

d = """
a = l + 1
k = l + 2
b = a + 3
c = a + k
m = k + 4
d = b + c
e = d + 5
f = d + g
j = e + 6
i = e + f
h = f + 7
"""
v = [Variable('i'), Variable('j'), Variable('h'), Variable('m')]
d = """
a = d + c
b = c + e
"""
v = [Variable('a'), Variable('b')]
e = flow_to_meta_state(d).label()[1]
pprint(d)
pprint(e)
print(CodeGenerator(env=e, out_vars=v).generate().format())
import sys; sys.exit()

p = """
if a < 0:
    if b < 0:
        x = 1
    else:
        x = 2
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

n = branch_merge(m, v)
pprint('merge')
pprint(n)

pprint('generate')
print(generate(n, v).format())
