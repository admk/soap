#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


from __future__ import print_function
import random

from expr import Expr, ExprTreeTransformer


e = '((a + 2) * (a + 3))'
t = Expr(e)
print('Expr:', e)
print('Tree:', t.tree())
s = ExprTreeTransformer(t, validate=True, print_progress=True).closure()
for n in s:
    print('>', n)
print('Validating...')
t = random.sample(s, 1)[0]
print('Sample Expr:', t)
r = ExprTreeTransformer(t, print_progress=True).closure()
if s >= r:
    print('Validated.')
else:
    print('Inconsistent closure generated.')
