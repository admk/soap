from soap.context.soap import SoapContext


context = dict(
    # debugging
    ipdb=False,
    # interactive shell
    autocall=True,
    xmode='verbose',
    repr=repr,
    # general
    multiprocessing=True,
    # analysis related
    unroll_factor=50,
    widen_factor=100,
    precision='single',
    norm='mse_error',
    # transform related
    max_steps=10,
    plugin_every=1,
    bool_steps=4,
    window_depth=2,
    unroll_depth=3,
)
context = SoapContext(context)
