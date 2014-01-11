from soap.label.base import Label
from soap.label.iteration import Iteration


class Annotation(Label * Iteration):
    __slots__ = ()

    def __init__(self, label=None, iteration=None, top=False, bottom=False):
        super().__init__(
            top=top, bottom=bottom, self_obj=label, other_obj=iteration)

    @property
    def label(self):
        return self.components[0]

    @property
    def iteration(self):
        return self.components[1]

    def __str__(self):
        return '({label}, {iteration})'.format(
            label=self.label, iteration=self.iteration)

    def __repr__(self):
        return '{cls}({label!r}, {iteration!r})'.format(
            cls=self.__class__.__name__,
            label=self.label, iteration=self.iteration)
