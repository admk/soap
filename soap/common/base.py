import inspect


class DynamicMethods(object):
    __slots__ = ()

    @classmethod
    def list_method_names(cls, predicate):
        """Find all transform methods within the class that satisfies the
        predicate.

        Returns:
            A list of tuples containing method names.
        """
        methods = [member[0] for member in inspect.getmembers(cls,
                   predicate=inspect.isroutine)]
        return [m for m in methods if not m.startswith('_') and
                'list_method' not in m and predicate(m)]

    def list_methods(self, predicate):
        return [getattr(self, m) for m in self.list_method_names(predicate)]


class Comparable(object):
    __slots__ = ()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __ge__(self, other):
        return not self.__lt__(other)

    def __gt__(self, other):
        return not self.__eq__(other) and not self.__lt__(other)

    def __le__(self, other):
        return not self.__gt__(other)


class BaseDispatcher(object):

    def _dispatch(self, obj):
        from soap.semantics.error import (
            mpz_type, mpfr_type, Interval, ErrorSemantics
        )
        numeral_types = (mpz_type, mpfr_type, Interval, ErrorSemantics)
        base_name = self.dispatch_name
        if isinstance(obj, numeral_types):
            func_name = base_name + '_numeral'
        else:
            func_name = base_name + '_' + type(obj).__name__
        try:
            return getattr(self, func_name)
        except AttributeError:
            return getattr(self, 'generic_' + base_name)

    def _execute(self, obj, *args, **kwargs):
        func = self._dispatch(obj)
        return func(obj, *args, **kwargs)

    def __call__(self, obj, *args, **kwargs):
        return self._execute(obj, *args, **kwargs)


def base_dispatcher(dispatch_name='execute', execute_name='execute'):
    class Dispatcher(BaseDispatcher):
        pass
    setattr(Dispatcher, execute_name, Dispatcher._execute)
    Dispatcher.dispatch_name = dispatch_name
    return Dispatcher
