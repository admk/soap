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
    _final_value_is_key = True

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
            ''.format(key))

    def _increment(self, value, identifier):
        if isinstance(value, Lattice):
            if value.is_top() or value.is_bottom():
                return value
        if is_numeral(value):
            return value
        if isinstance(value, Expression):
            args = [self._increment(a, identifier) for a in value.args]
            return expression_factory(value.op, *args)
        if isinstance(value, Identifier):
            if value.variable == identifier.variable:
                if value.label == identifier.label:
                    return value.prev_iteration()
            return value
        raise TypeError('Do not know how to increment {!r}'.format(value))

    def increment(self, key, value):
        if self.is_top():
            # if conflict, return itself
            return self
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
        if self._final_value_is_key:
            value = key
        incr_map[key.global_final()] = value
        return self.__class__(incr_map)
