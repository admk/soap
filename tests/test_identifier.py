import unittest

from soap.expression import expr
from soap.label.annotation import Annotation
from soap.label.base import Label
from soap.label.identifier import Identifier
from soap.label.iteration import Iteration


class TestAnnotation(unittest.TestCase):
    """Unittesting for :class:`soap.identifier.Annotation`."""
    def setUp(self):
        self.bot = Annotation(bottom=True)
        self.top = Annotation(top=True)
        self.x11 = Annotation(
            label=Label(expr('x'), 1), iteration=Iteration(1))
        self.x12 = Annotation(
            label=Label(expr('x'), 1), iteration=Iteration(2))
        self.x21 = Annotation(
            label=Label(expr('x'), 2), iteration=Iteration(1))
        self.x1t = Annotation(
            label=Label(expr('x'), 1), iteration=Iteration(top=True))
        self.xt1 = Annotation(
            label=Label(top=True), iteration=Iteration(1))
        self.xt2 = Annotation(
            label=Label(top=True), iteration=Iteration(2))

    def test_attributes(self):
        self.assertTrue(self.bot.label.is_bottom())
        self.assertTrue(self.bot.iteration.is_bottom())
        self.assertTrue(self.top.label.is_top())
        self.assertTrue(self.top.iteration.is_top())

    def test_order(self):
        self.assertLessEqual(self.bot, self.x11)
        self.assertLessEqual(self.x11, self.x1t)
        self.assertLessEqual(self.x11, self.xt1)
        self.assertLessEqual(self.x1t, self.top)
        self.assertLessEqual(self.xt1, self.top)

    def test_join(self):
        self.assertEqual(self.bot | self.x11, self.x11)
        self.assertEqual(self.x11 | self.x12, self.x12)
        self.assertEqual(self.x11 | self.x21, self.xt1)
        self.assertEqual(self.x12 | self.x21, self.xt2)


class TestIdentifier(unittest.TestCase):
    """Unittesting for :class:`soap.identifier.Identifier`."""
    def setUp(self):
        variable = expr('x')
        self.label = Label(variable)
        self.iteration = Iteration(1)
        self.annotation = Annotation(self.label, self.iteration)
        self.identifier = Identifier(variable, annotation=self.annotation)

    def test_attributes(self):
        self.assertEqual(self.identifier.label, self.label)
        self.assertEqual(self.identifier.iteration, self.iteration)

    def test_iteration_utilities(self):
        self.assertEqual(
            self.identifier.initial().iteration, Iteration(top=True))
        self.assertEqual(
            self.identifier.final().iteration, Iteration(bottom=True))
        self.assertEqual(
            self.identifier.global_initial().label, Label(top=True))
        self.assertEqual(
            self.identifier.global_initial().iteration, Iteration(top=True))
        self.assertEqual(
            self.identifier.global_final().label, Label(bottom=True))
        self.assertEqual(
            self.identifier.global_final().iteration, Iteration(bottom=True))
        self.assertEqual(
            self.identifier.prev_iteration().iteration,
            Iteration(int(self.iteration) + 1))
