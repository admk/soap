from soap.expression import Variable
from soap.label import Identifier
from soap.semantics.state.base import BaseState


class IdentifierBaseState(BaseState):
    """The program analysis domain object based on intervals and error
    semantics.
    """
    __slots__ = ()

    def _cast_key(self, key):
        """Convert a variable into an identifier.

        A current identifier of a variable is always::
            ([variable_name], ⊥, ⊥)
        """
        if isinstance(key, Identifier):
            return key
        if isinstance(key, Variable):
            return Identifier(key)
        if isinstance(key, str):
            return Identifier(Variable(key))
        raise TypeError(
            'Do not know how to convert key {!r} into an identifier.'
            .format(key))

    def filter(self, predicate):
        items = {}
        for identifier, value in self.items():
            if predicate(identifier):
                items[identifier] = value
        return self.__class__(items)
