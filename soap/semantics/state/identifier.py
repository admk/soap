from soap.expression import Expression, expression_factory, Variable
from soap.label import Annotation, Identifier
from soap.lattice import Lattice
from soap.semantics.common import is_numeral
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
            return Identifier(key, annotation=Annotation(bottom=True))
        if isinstance(key, str):
            return self._cast_key(Variable(key))
        raise TypeError(
            'Do not know how to convert key {!r} into an identifier.'
            .format(key))

    def filter(self, variable=None, label=None, iteration=None):
        kwargs = {
            'variable': variable,
            'label': label,
            'iteration': iteration,
        }
        items = {}
        for identifier, value in self.items():
            for attr, attr_val in kwargs.items():
                if attr_val is not None:
                    if getattr(identifier, attr) != attr_val:
                        break
            else:
                items[identifier] = value
        return self.__class__(items)
