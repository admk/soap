from soap.context.soap import SoapContext


context = dict(
    # debugging
    ipdb=False,
    # interactive shell
    autocall=True,
    xmode='verbose',
    repr=repr,
    # analysis related
    unroll_factor=50,
    widen_factor=100,
    precision='single',
    window_depth=2,
    unroll_depth=3,
    norm='mse_error',
    multiprocessing=True,
    bool_steps=4,
)
context = SoapContext(context)
