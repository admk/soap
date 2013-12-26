from soap.label.base import Label
from soap.label.iteration import Iteration


class Annotation(Label * Iteration):
    __slots__ = ('label', 'iteration')

    def __init__(self, label=None, iteration=None, top=False, bottom=False):
        self.label = label or Label(bottom=True)
        self.iteration = iteration or Iteration(bottom=True)
        super().__init__(
            top=top, bottom=bottom, self_obj=label, other_obj=iteration)

    def is_bottom(self):
        return self.label.is_bottom()

    def is_top(self):
        return self.label.is_top()

    def __str__(self):
        return '({label}, {iteration})'.format(
            label=self.label, iteration=self.iteration)

    def __repr__(self):
        return '{cls}({label!r}, {iteration!r})'.format(
            cls=self.__class__.__name__,
            label=self.label, iteration=self.iteration)
