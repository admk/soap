from soap.semantics.common import is_numeral


class BaseDispatcher(object):

    def generic_execute(self, *args, **kwargs):
        raise NotImplementedError

    def _dispatch(self, expr):
        if is_numeral(expr):
            func_name = 'execute_numeral'
        else:
            func_name = 'execute_{}'.format(expr.__class__.__name__)
        return getattr(self, func_name, self.generic_execute)

    def execute(self, expr, *args, **kwargs):
        func = self._dispatch(expr)
        return func(expr, *args, **kwargs)

    def __call__(self, expr, *args, **kwargs):
        return self.execute(expr, *args, **kwargs)
