from soap.context.soap import SoapContext


context = SoapContext(
    # interactive shell
    autocall=True,
    xmode='verbose',
    repr=str,
    # analysis related
    unroll_factor=50,
    widen_factor=100,
    precision='single',
    window_depth=2,
    program_depth=3,
)
