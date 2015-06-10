from soap.context.soap import SoapContext


context = dict(
    # debugging
    ipdb=False,
    # interactive shell
    autocall=True,
    xmode='context',
    # general
    repr=str,
    multiprocessing=True,
    # platform
    device='Virtex7',
    frequency=100,
    port_count=2,
    # analysis related
    unroll_factor=50,   # how many steps before no unrolling in static analysis
    widen_factor=100,   # how many steps before widening in static analysis
    precision='single',
    norm='mse_error',   # function for computing multiple variable avg error
    ii_precision=5,     # how precise are IIs computed
    scheduler='alap',   # the scheduler used for sequential nodes
    # transform related
    rand_seed=42,
    sample_unique=True,
    reduce_limit=2000,
    size_limit=500,
    loop_size_limit=50,
    algorithm='greedy',
    max_steps=5,        # max no of steps for equivalent expr discovery
    plugin_every=1,     # no of steps before plugins are executed
    thickness=3,        # no of iterations of pareto suboptimal inclusion
    bool_steps=5,       # transition steps for finding equivalent boolean exprs
    window_depth=2,     # depth limit window for equivalent expr discovery
    unroll_depth=2,     # partial unroll depth limit
)
context = SoapContext(context)
