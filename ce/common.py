#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


import inspect


class DynamicMethods(object):

    def list_methods(self, predicate):
        """Find all transform methods within the class that satisfies the
        predicate.

        Returns:
            A list of tuples containing method names and corresponding methods
            that can be called with a tree as the argument for each method.
        """
        methods = [member[0] for member in inspect.getmembers(
            self.__class__, predicate=inspect.ismethod)]
        return [getattr(self, method) for method in methods
                if not method.startswith('_') and method != 'list_methods' and
                predicate(method)]


class Comparable(object):

    def __eq__(self, other):
        return not self < other and not other < self

    def __ne__(self, other):
        return self < other or other < self

    def __ge__(self, other):
        return not self < other

    def __gt__(self, other):
        return other < self

    def __le__(self, other):
        return not other < self
