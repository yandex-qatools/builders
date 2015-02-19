'''
Checks that all the modifiers are picklable and unpicklable

Created on Jan 17, 2014

@author: pupssman
'''
from builders.construct import Collection, Unique, Maybe
from builders.model_graph import BuilderModelClass
from builders.modifiers import InstanceModifier, NumberOf, ValuesMixin, Given, \
    HavingIn, Enabled, OneOf
import pickle
import pytest


class A(ValuesMixin, BuilderModelClass):
    a = 1


class B(BuilderModelClass):
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
