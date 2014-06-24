import contextlib
import os

from soap.context.soap import SoapContext


context = dict(
    # interactive shell
    autocall=True,
    xmode='verbose',
    repr=str,
    # analysis related
    unroll_factor=50,
    widen_factor=100,
    precision='single',
    window_depth=2,
    unroll_depth=3,
)


with open(os.devnull, 'w') as null:
    with contextlib.redirect_stdout(null):
        context = SoapContext(context)
