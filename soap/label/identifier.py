from soap.common.formatting import superscript
from soap.expression.variable import Variable
from soap.label.base import Label


class Identifier(Variable * Label):
    __slots__ = ()

    def __init__(self, variable, label=None, top=False, bottom=False):
        label = label or Label(bottom=True)
        super().__init__(variable, label, top=top, bottom=bottom)

    @property
    def variable(self):
        return self.components[0]

    @property
    def label(self):
        return self.components[1]

    def __str__(self):
        return '{variable}{label}'.format(
            variable=self.variable, label=superscript(self.label))

    def __repr__(self):
        return '{cls}({variable!r}, {label!r})'.format(
            cls=self.__class__.__name__,
            variable=self.variable, label=self.label)
