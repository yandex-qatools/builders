'''
Checks that all the modifiers are picklable and unpicklable

Created on Jan 17, 2014

@author: pupssman
'''
import pickle
import pytest
from builders.modifiers import InstanceModifier, NumberOf, ValuesMixin, Given, \
    HavingIn, Enabled, OneOf
from builders.construct import Collection, Unique, Maybe


class A(ValuesMixin):
    a = 1


class B:
    a = Unique(A)
    ma = Maybe(Unique(A))
    aa = Collection(A)


def foo(a):
    pass


@pytest.mark.parametrize('modifier', [InstanceModifier(A).thatDoes(foo),
                                      InstanceModifier(A).thatSets(a=2),
                                      InstanceModifier(A).thatCarefullySets(a=2),
                                      A.values(a=2),
                                      NumberOf(B.aa, 2),
                                      HavingIn(B.aa, A()),
                                      Given(B.a, A()),
                                      Enabled(B.ma),
                                      OneOf(B.aa, [[]])
                                      ])
def test_modifier(modifier):
    assert pickle.loads(pickle.dumps(modifier))
