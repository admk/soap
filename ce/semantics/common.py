#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :


_label_count = 0
_labels = {}


def fresh_int(e):
    if e in _labels:
        return _labels[e]
    global _label_count, _labels
    _label_count += 1
    _labels[e] = _label_count
    return _label_count


class Label(object):

    def __init__(self, e, l=None):
        self.l = l or fresh_int(e)
        self.e = e
        self.__slots__ = []
        super(Label, self).__init__()

    def __str__(self):
        return 'l%s' % str(self.l)

    def __repr__(self):
        return 'Label(%s, %s)' % (repr(self.e), repr(self.l))

    def __eq__(self, other):
        if not isinstance(other, Label):
            return False
        return self.l == other.l

    def __lt__(self, other):
        if not isinstance(other, Label):
            return False
        return self.l < other.l

    def __hash__(self):
        return hash(self.l)


class Labels(object):

    def __init__(self, s):
        self.s = {fresh_int: e for e in s}
        super(Labels, self).__init__()

    def add(self, e):
        if e in self.s.items():
            return
        self.s[Label()] = e


class Lattice(object):

    def join(self, other):
        raise NotImplementedError

    def meet(self, other):
        raise NotImplementedError

    def __or__(self, other):
        return self.join(other)

    def __and__(self, other):
        return self.meet(other)
