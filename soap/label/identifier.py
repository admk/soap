from soap.expression.variable import Variable
from soap.label.iteration import Iteration
from soap.label.annotation import Annotation


class Identifier(Variable * Annotation):
    __slots__ = ()

    def __init__(self, variable, label=None, iteration=None,
                 annotation=None, top=False, bottom=False):
        annotation = annotation or Annotation(
            label, iteration, top=top, bottom=bottom)
        super().__init__(variable, annotation, top=top, bottom=bottom)

    @property
    def variable(self):
        return self.components[0]

    @property
    def annotation(self):
        return self.components[1]

    @property
    def label(self):
        return self.annotation.label

    @property
    def iteration(self):
        return self.annotation.iteration

    def initial(self):
        return Identifier(self.variable, annotation=Annotation(
            self.annotation.label, Iteration(top=True)))

    def final(self):
        return Identifier(self.variable, annotation=Annotation(
            self.annotation.label, Iteration(bottom=True)))

    def global_initial(self):
        return Identifier(self.variable, annotation=Annotation(top=True))

    def global_final(self):
        return Identifier(self.variable, annotation=Annotation(bottom=True))

    def prev_iteration(self):
        if self.iteration.is_bottom():
            iteration = Iteration(0)
        else:
            iteration = self.iteration
        return Identifier(
            self.variable, label=self.label, iteration=(iteration + 1))

    def __str__(self):
        from soap.label import superscript
        return '{variable}{annotation}'.format(
            variable=self.variable, annotation=superscript(self.annotation))

    def __repr__(self):
        return '{cls}({variable!r}, {label!r}, {iteration!r})'.format(
            cls=self.__class__.__name__, variable=self.variable,
            label=self.annotation.label, iteration=self.annotation.iteration)
