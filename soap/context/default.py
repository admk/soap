from soap.context.soap import SoapContext


context = SoapContext()
with context.no_invalidate_cache():
    context.unroll_factor = 50
    context.widen_factor = 100
    context.precision = 'single'
    context.window_depth = 2
    context.program_depth = 3
