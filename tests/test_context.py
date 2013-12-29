import copy
import unittest

from soap.context.base import _Context


class TestContext(unittest.TestCase):
    """Unittesting for :class:`soap.context._Context`.  """
    def setUp(self):
        self.context = _Context(a=1, b={'c': {'d': 2}})

    def test_init(self):
        self.assertIsInstance(self.context.b, _Context)
        self.assertIsInstance(self.context.b.c, _Context)

    def test_getter(self):
        self.assertEqual(self.context.a, 1)
        self.assertEqual(self.context.b.c.d, 2)

    def test_setter(self):
        context = copy.deepcopy(self.context)
        context.a = 3
        context.b.c.d = 4
        context.b.e = 5
        context.f = {}
        self.assertEqual(context.a, 3)
        self.assertEqual(context.b.c.d, 4)
        self.assertEqual(context.b.e, 5)
        self.assertIsInstance(context.f, _Context)

    def test_deleter(self):
        context = copy.deepcopy(self.context)
        del context.a
        self.assertNotIn('a', context)

    def test_snapshot(self):
        original_context = copy.deepcopy(self.context)
        self.context.take_snapshot()
        self.context.a = 3
        self.context.b.c.d = 4
        self.context.b.e = 5
        self.assertEqual(self.context.a, 3)
        self.assertEqual(self.context.b.c.d, 4)
        self.assertEqual(self.context.b.e, 5)
        self.context.restore_snapshot()
        self.assertEqual(self.context, original_context)

    def test_local(self):
        context = copy.deepcopy(self.context)
        context.a = 1
        with context.local(a=2):
            self.assertEqual(context.a, 2)
            context.e = 3
        self.assertEqual(context.a, 1)
        self.assertNotIn('e', context)
        context.c = {}
        with context.c.local(d=4):
            self.assertEqual(context.c.d, 4)
        self.assertFalse(context.c)

    def test_recursive_local(self):
        context = copy.deepcopy(self.context)
        with context.local(a=3):
            context.outter = True
            self.assertEqual(context.a, 3)
            with context.local(b=4):
                context.inner = True
                self.assertEqual(context.b, 4)
            self.assertNotIn('inner', context)
            self.assertTrue(context.outter)
            self.assertEqual(context.b, self.context.b)
        self.assertEqual(context, self.context)

    def test_chain_local(self):
        context = copy.deepcopy(self.context)
        with context.b.local(c=3):
            self.assertEqual(context.b.c, 3)
        self.assertEqual(context, self.context)

    def test_hook(self):
        class HookContext(_Context):
            def __init__(hook_self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                hook_self.reached = False

            def b_hook(hook_self, key, value):
                self.assertEqual(key, 'b')
                hook_self.reached = True
                return key, value

        context = HookContext()
        self.assertFalse(context.reached)
        context.a = 1
        self.assertFalse(context.reached)
        context.b = 1
        self.assertTrue(context.reached)
