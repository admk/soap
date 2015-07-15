from soap.context.soap import SoapContext


context = dict(
    # debugging
    ipdb=False,
    # interactive shell
    autocall=True,
    xmode='context',
    # general
    repr=repr,
    multiprocessing=False,
    # platform
    device='Virtex7',
    frequency=333,
    port_count=2,
    # analysis related
    fast_outer=True,     # analyze only innermost loop for error
    fast_factor=0.2,     # accelerate error analysis by computing a fraction
                         # of iterations and extrapolate
    scalar_array=True,
    unroll_factor=0,     # steps before no unrolling in static analysis
    widen_factor=0,      # steps before widening in static analysis
    precision='single',
    norm='mse_error',    # function for computing multiple variable avg error
    ii_precision=5,      # how precise are IIs computed
    round_values=True,
    scheduler='alap',    # the scheduler used for sequential nodes
    # transform related
    rand_seed=42,
    sample_unique=True,
    reduce_limit=2000,
    size_limit=500,
    loop_size_limit=0,
    algorithm='partition',
    max_steps=10,        # max no of steps for equivalent expr discovery
    plugin_every=1,      # no of steps before plugins are executed
    thickness=0,         # no of iterations of pareto suboptimal inclusion
    small_steps=5,       # transition steps for finding equivalent small exprs
    small_depth=3,       # transition depth for finding equivalent small exprs
    window_depth=3,      # depth limit window for equivalent expr discovery
    unroll_depth=2,      # partial unroll depth limit
)
context = SoapContext(context)
