#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


from __future__ import print_function
import random
from pprint import pprint

from expr import ExprParser, ExprTreeTransformer


e = '((a + 1) * (b + 1))'
t = ExprParser(e).tree
print('Expr:', e)
print('Tree:')
pprint(t)
s = ExprTreeTransformer(t, print_progress=True).closure()
print('Validating...')
t = random.sample(s, 1)[0]
print('Sample Expr:', ExprParser(t))
r = ExprTreeTransformer(t).closure()
if s == r:
    print('Validated.')
else:
    print('Inconsistent closure generated.')
