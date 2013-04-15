import inspect


class DynamicMethods(object):

    def list_method_names(self, predicate):
        """Find all transform methods within the class that satisfies the
        predicate.

        Returns:
            A list of tuples containing method names.
        """
        methods = [member[0] for member in inspect.getmembers(self,
                   predicate=inspect.isroutine)]
        return [m for m in methods if not m.startswith('_') and
                m != 'list_ms' and predicate(m)]

    def list_methods(self, predicate):
        return [getattr(self, m) for m in self.list_method_names(predicate)]


class Comparable(object):

    def __ne__(self, other):
        return not self.__eq__(other)

    def __ge__(self, other):
        return not self.__lt__(other)

    def __gt__(self, other):
        return not self.__eq__(other) and not self.__lt__(other)

    def __le__(self, other):
        return not self.__gt__(other)
