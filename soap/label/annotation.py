from soap.label.base import Label
from soap.label.iteration import Iteration


class Annotation(Label * Iteration):
    __slots__ = ()

    def __init__(self, label=None, iteration=None, top=False, bottom=False):
        iteration = iteration or Iteration(bottom=True)
        super().__init__(label, iteration, top=top, bottom=bottom)

    @property
    def label(self):
        return self.components[0]

    @property
    def iteration(self):
        return self.components[1]

    def attributed(self, attribute):
        return self.__class__(self.label.attributed(attribute), self.iteration)

    def attributed_true(self):
        return self.attributed('tt')

    def attributed_false(self):
        return self.attributed('ff')

    def attributed_conditional(self):
        return self.attributed('cl')

    def __str__(self):
        if self.iteration.is_bottom():
            return str(self.label)
        return '({label}, {iteration})'.format(
            label=self.label, iteration=self.iteration)

    def __repr__(self):
        return '{cls}({label!r}, {iteration!r})'.format(
            cls=self.__class__.__name__,
            label=self.label, iteration=self.iteration)
