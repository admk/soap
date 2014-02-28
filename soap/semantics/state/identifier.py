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

    def increment_item(self, value, identifier):
        if isinstance(value, Lattice):
            if value.is_top() or value.is_bottom():
                return value
        if is_numeral(value):
            return value
        if isinstance(value, Expression):
            args = [self.increment_item(a, identifier) for a in value.args]
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
            self.increment_item(k, key): self.increment_item(v, key)
            for k, v in self.items()
        }
        # now use the incremented value for assignment
        incr_map[key] = self.increment_item(value, key)
        # update final key
        incr_map[key.global_final()] = key
        return self.__class__(incr_map)

    def _post_conditional_join_value(
            self, final_key, true_value, false_value, annotation):
        raise NotImplementedError

    def post_conditional(self, expr, true_state, false_state, annotation):
        mapping = {}
        for k, v in set(true_state.items()) | set(false_state.items()):
            # if is not final identifier, keep its value
            if not k.annotation.is_bottom():
                existing_value = mapping.get(k)
                if existing_value and existing_value != v:
                    raise ValueError(
                        'Conflict in mapping update, same key {k}, '
                        'but different values {v}, {existing_value}'.format(
                            k=k, v=v, existing_value=existing_value))
                mapping[k] = v
                continue
            # if k is final, join values for k in true & false states
            join_id = Identifier(k.variable, annotation=annotation)
            mapping[k] = join_id
            mapping[join_id] = self._post_conditional_join_value(
                k, true_state[k], false_state[k], annotation)
        return self.__class__(mapping)

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
