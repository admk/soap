from soap.expression import Variable
from soap.label import Annotation, Identifier
from soap.semantics.state.base import BaseState


class IdentifierBaseState(BaseState):
    """The program analysis domain object based on intervals and error
    semantics.
    """
    __slots__ = ()

    def __setitem__a(self, key, value):
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
        super().__setitem__(
            *self._key_value_for_current_iteration(key, value))
        # also updates the global current identifier
        key, value = self._key_value_for_bottom_iteration(key, value)
        if key != value:
            super().__setitem__(key, value)

    def _key_value_for_top_iteration(self, key, value):
        raise NotImplementedError

    def _key_value_for_consecutive_iteration(self, key, value):
        raise NotImplementedError

    def _key_value_for_current_iteration(self, key, value):
        raise NotImplementedError

    def _key_value_for_bottom_iteration(self, key, value):
        raise NotImplementedError

    def _increment(self, key, value, identifier):
        raise NotImplementedError

    def __getitem__(self, key):
        if isinstance(key, slice):
            return self.increment(key.start, key.stop)
        return super().__getitem__(key)

    def increment(self, key, value):
        key, value = self._cast_key(key), self._cast_value(value)
        if not key.iteration.is_bottom():
            raise ValueError('Incrementer must be current.')
        if key.label.is_bottom():
            # no label, don't know how to increment
            incr_map = dict(self)
            incr_map[key] = value
            return self.__class__(incr_map)
        # increment iterations for previous assignments
        incr_map = {
            self._increment(k, key): self._increment(v, key)
            for k, v in self.items()
        }
        # now use the incremented value for assignment
        incr_map[key] = self._increment(value, key)
        # update final key
        incr_map[key.global_final()] = key
        return self.__class__(incr_map)

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
        raise TypeError('Do not know how to convert key {!r}'.format(key))
