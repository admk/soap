from soap.expression import Variable
from soap.label import Annotation, Identifier
from soap.semantics.state.base import BaseState


class IdentifierBaseState(BaseState):
    """The program analysis domain object based on intervals and error
    semantics.
    """
    __slots__ = ()

    def __setitem__(self, key, value):
        # increment iterations for key value pair
        key, value = self._cast_key(key), self._cast_value(value)
        if key.iteration.is_top():
            # depth limit reached
            return super().__setitem__(
                *self._key_value_for_top_iteration(key, value))
        # recursively update values for previous iterations before overwriting
        self.__setitem__(
            *self._key_value_for_consecutive_iteration(key, value))
        # update current iteration
        super().__setitem__(key, value)
        # also updates the current identifier
        super().__setitem__(key.global_final(), value)

    def _key_value_for_top_iteration(self, key, value):
        raise NotImplementedError

    def _key_value_for_consecutive_iteration(self, key, value):
        raise NotImplementedError

    def _cast_key(self, key):
        """Convert a variable into an identifier.

        A current identifier of a variable is always::
            ([variable_name], ⊥, ⊥)
        """
        if isinstance(key, str):
            key = Variable(key)
        if isinstance(key, Variable):
            return Identifier(key, annotation=Annotation(bottom=True))
        if isinstance(key, Identifier):
            return key
        raise TypeError('Do not know how to convert key {!r}'.format(key))
