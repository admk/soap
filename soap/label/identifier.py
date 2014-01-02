from soap.label.iteration import Iteration
from soap.label.annotation import Annotation


class Identifier(object):
    __slots__ = ('variable', 'annotation')

    def __init__(self, variable, label=None, iteration=None, annotation=None):
        super().__init__()
        self.variable = variable
        self.annotation = (
            annotation or Annotation(label=label, iteration=iteration))

    @property
    def label(self):
        return self.annotation.label

    @property
    def iteration(self):
        return self.annotation.iteration

    def initial(self):
        return Identifier(self.variable, annotation=Annotation(top=True))

    def final(self):
        return Identifier(self.variable, annotation=Annotation(bottom=True))

    def prev_iteration(self):
        if self.iteration.is_bottom():
            iteration = Iteration(0)
        else:
            iteration = self.iteration
        return Identifier(
            self.variable, label=self.label, iteration=(iteration + 1))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.variable != other.variable:
            return False
        return self.annotation == other.annotation

    def __hash__(self):
        return hash((self.__class__, self.variable, self.annotation))

    def __str__(self):
        return '({variable}, {label}, {iteration})'.format(
            variable=self.variable,
            label=self.annotation.label, iteration=self.annotation.iteration)

    def __repr__(self):
        return '{cls}({variable!r}, {label!r}, {iteration!r})'.format(
            cls=self.__class__.__name__, variable=self.variable,
            label=self.annotation.label, iteration=self.annotation.iteration)
