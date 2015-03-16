from builders.builder import Builder
from builders.construct import Unique, Collection, Uplink, Maybe, Lambda, Random
from builders.model_graph import BuilderModelClass
from builders.modifiers import Given, InstanceModifier, NumberOf, HavingIn, \
    OneOf, Enabled, ValuesMixin, LambdaModifier, Another, Disabled
from random import randint
import pytest



class A(BuilderModelClass):
    value = 1


class B(BuilderModelClass):
    a = Unique(A)


class C(BuilderModelClass):
        b = Unique(B)


def test_class_modifier_as_class():
    def set_value(instance):
        A.value = 5

    M = InstanceModifier(A).thatDoes(set_value)

    a = Builder(A).withA(M).build()

    assert isinstance(a, A)
    assert a.value == 5


def test_class_modifiers_over_lambda():
    modifier = InstanceModifier(A).thatDoes(lambda a: setattr(a, 'value', 8))

    a = Builder(A).withA(modifier).build()

    assert isinstance(a, A)
    assert a.value == 8


def test_given():
    modifier = Given(B.a, 8)

    b = Builder(B).withA(modifier).build()
    assert b.a == 8


def test_more_given():
    modifier = Given(B.a, 8)

    c = Builder(C).withA(modifier).build()
    assert c.b.a == 8


def test_given_chains():
    c = Builder(C).build()
    c2 = Builder(C).withA(Given(B.a, c.b.a)).build()

    assert c2.b.a == c.b.a

    c3 = Builder(C).withA(Given(C.b, c.b)).build()

    assert c3.b == c.b


def test_not_touches():
    class A(BuilderModelClass):
        pass

    class B(BuilderModelClass):
        a = Unique(A)

    b1 = Builder(B).withA(Given(B.a, 8)).build()
    assert b1.a == 8

    b2 = Builder(B).build()

    assert isinstance(b2.a, A)


def test_modifies_dont_affect_given():
    class A(BuilderModelClass):
        value = 0

    class B(BuilderModelClass):
        a = Unique(A)

    myA = A()
    myA.value = 1

    b = Builder(B).withA(Given(B.a, myA)).withA(InstanceModifier(A).thatSets(value=5)).build()

    assert b.a.value == 1
    assert b.a == myA


def test_having():
    class A(BuilderModelClass):
        pass

    class B(BuilderModelClass):
        a = Collection(A)

    def check(b, num):
        assert b.a
        assert b.a[0]
        assert isinstance(b.a[0], A)
        assert len(b.a) == num

    b = Builder(B).build()
    b2 = Builder(B).withA(NumberOf(B.a, 3)).build()
    b3 = Builder(B).build()

    check(b, 1)
    check(b2, 3)
    check(b3, 1)

    assert b2.a[0] != b2.a[1]
    assert b2.a[0] != b2.a[2]


def test_Having_instances():
    class A(BuilderModelClass):
        pass

    class B(BuilderModelClass):
        a = Collection(A)

    myA = A()
    b = Builder(B).withA(HavingIn(B.a, myA)).build()

    assert myA in b.a

    b2 = Builder(B).withA(HavingIn(B.a, myA)).withA(NumberOf(B.a, 3)).build()
    assert myA in b2.a
    assert len(b2.a) == 3


def test_thatSets():
    class A(BuilderModelClass):
        pass

    a = Builder(A).withA(InstanceModifier(A).thatSets(ololo=1, hahaha=2)).build()
    assert a.ololo == 1
    assert a.hahaha == 2


def test_one_of():
    class A(BuilderModelClass):
        a = 0
        b = Uplink()

    class B(BuilderModelClass):
        values = Collection(A, uplink=A.b)

    #A.b.linksTo(B, B.values)

    b = Builder(B).withA(NumberOf(B.values, 3)).\
        withA(OneOf(B.values, InstanceModifier(A).thatSets(a=8))).\
        withA(OneOf(B.values, InstanceModifier(A).thatSets(a=5))).\
        build()

    assert len(b.values) == 3
    assert len([a for a in b.values if a.a == 8]) == 1
    assert len([a for a in b.values if a.a == 5]) == 1


def test_maybe():
    class A(BuilderModelClass):
        b = Uplink()

    class B(BuilderModelClass):
        a = Maybe(Unique(A, uplink=A.b))

    #A.b.linksTo(B, B.a)

    b1 = Builder(B).build()
    b2 = Builder(B).withA(Enabled(B.a)).build()
    a = Builder(A).withA(Enabled(B.a)).build()

    assert not b1.a
    assert isinstance(b2.a, A)
    assert b2.a.b == b2
    assert a.b.a == a


class CarefulA(BuilderModelClass):
    ololo = 0
    hahaha = 0


def test_thatSetsCarefully_works():
    a = Builder(CarefulA).withA(InstanceModifier(CarefulA).thatCarefullySets(ololo=1, hahaha=2)).build()
    assert a.ololo == 1
    assert a.hahaha == 2


def test_thatSetsCarefully_is_careful():
    with pytest.raises(AssertionError) as e:
        Builder(CarefulA).withA(InstanceModifier(CarefulA).thatCarefullySets(foo='bar')).build()

    assert 'foo' in e.value.message
    assert 'missing' in e.value.message


def test_sum():
    mod_1 = InstanceModifier(A).thatSets(x=1)
    mod_2 = InstanceModifier(B).thatSets(x=1)

    assert mod_1 + mod_2 == [mod_1, mod_2]


def test_lambda_modifier_changes_function():
    class A(BuilderModelClass):
        a = Lambda(lambda _: 1)

    assert Builder(A).withA(LambdaModifier(A.a, lambda _: 2)).build().a == 2


def test_lambda_modifier_function_is_set_back():
    class A(BuilderModelClass):
        a = Lambda(lambda _: 1)

    Builder(A).withA(LambdaModifier(A.a, lambda _: 2)).build()
    assert Builder(A).build().a == 1


def test_lambda_modifier_raises_given_not_lambda():
    class A(BuilderModelClass):
        a = Random()

    with pytest.raises(TypeError):
        Builder(A).withA(LambdaModifier(A.a, lambda _: 2)).build()


class Foo(ValuesMixin, BuilderModelClass):
        bar = 0
        baz = ''


def test_values_mixin(monkeypatch):
    assert Builder(Foo).withA(Foo.values(bar=1)).build().bar == 1
    assert Builder(Foo).withA(Foo.values(baz='baz')).build().baz == 'baz'


def test_another_modifier():
    class A(BuilderModelClass):
        a = 0
        b = Uplink()

    class B(BuilderModelClass):
        values = Collection(A, uplink=A.b)

    #A.b.linksTo(B, B.values)

    b = Builder(B).withA(NumberOf(B.values, 1)).\
        withA(Another(B.values, InstanceModifier(A).thatSets(a=4))).\
        withA(Another(B.values, InstanceModifier(A).thatSets(a=28))).build()

    assert len(b.values) == 3
    assert len([a for a in b.values if a.a == 0]) == 1
    assert len([a for a in b.values if a.a == 4]) == 1
    assert len([a for a in b.values if a.a == 28]) == 1


def test_maybe_default():
    class A(BuilderModelClass):
        pass

    class B(BuilderModelClass):
        a = Maybe(Unique(A), enabled=True)

    b1 = Builder(B).build()
    b2 = Builder(B).build()

    assert b1.a
    assert b2.a


def test_maybe_disabled():
    class A(BuilderModelClass):
        pass

    class B(BuilderModelClass):
        a = Maybe(Unique(A), enabled=True)

    b1 = Builder(B).withA(Disabled(B.a)).build()
    b2 = Builder(B).build()

    assert b1.a is None
    assert b2.a


def test_maybe_enabled():
    class A(BuilderModelClass):
        pass

    class B(BuilderModelClass):
        a = Maybe(Unique(A))

    b1 = Builder(B).withA(Enabled(B.a)).build()
    b2 = Builder(B).build()

    assert b1.a is not None
    assert b2.a is None


#class A1(BuilderModelClass):
#    b = Uplink()
#    c = Uplink()
#    id = Random()
#
#
#class B1(BuilderModelClass):
#    a = Collection(A1, number=0)
#
#
#class C1(BuilderModelClass):
#    a = Collection(A1, number=0)
#
#
#A1.b.linksTo(B1, B1.a)
#A1.c.linksTo(C1, C1.a)
#
#
#def test_grouped_collection():
#    a = Builder(A1).withA(Group(B1.a, 3, Same(A1, "id"))).build()
#    b = Builder(B1).withA(Group(B1.a, 3, Same(A1, "id"))).build()
#    
#    def check(b):
#        assert len(b.a) == 3
#        assert b.a[0].id == b.a[1].id and b.a[1].id == b.a[2].id
#
#    check(a.b)
#    check(b)
#    
#
#def test_2_groups_collection():
#    a = Builder(A1).withA([Group(B1.a, 2, Same(A1, "id")), Group(B1.a, 3, Same(A1, "id"))]).build()
#    b = Builder(B1).withA([Group(B1.a, 2, Same(A1, "id")), Group(B1.a, 3, Same(A1, "id"))]).build()
#    
#    def check(b):
#        assert len(b.a) == 5
#        assert b.a[0].id == b.a[1].id
#        assert b.a[1].id != b.a[2].id
#        assert b.a[2].id == b.a[3].id and b.a[3].id == b.a[4].id
#
#    check(a.b)
#    check(b)
#
#
#def test_2_uplinks_collection_groups():
#    a = Builder(A1).withA(Group(B1.a, 3, Same(A1, "c"))).build()
#    b = Builder(B1).withA(Group(B1.a, 3, Same(A1, "c"))).build()
#    
#    def check(b):
#        assert len(b.a) == 3
#        assert id(b.a[0].c) == id(b.a[1].c) and id(b.a[1].c) == id(b.a[2].c)
#        assert len(b.a[0].c.a) == 3
#        assert b.a[0].id != b.a[1].id and b.a[1].id != b.a[2].id and b.a[0].id != b.a[2].id
#        
#        c = b.a[0].c
#        
#        assert b.a[0] == c.a[0] and b.a[1] == c.a[1] and b.a[2] == c.a[2]
#        
#    check(a.b)
#    check(b)
#
#
#def test_2_group_rules():
#    a = Builder(A1).withA(Group(B1.a, 3, Same(A1, "c"), Same(A1, "id"))).build()
#    b = Builder(B1).withA(Group(B1.a, 3, Same(A1, "c"), Same(A1, "id"))).build()
#    
#    def check(b):
#        assert b.a[0].id == b.a[1].id and b.a[1].id == b.a[2].id
#        assert id(b.a[0].c) == id(b.a[1].c) and id(b.a[1].c) == id(b.a[2].c)
#        assert len(b.a[0].c.a) == 3
#
#    check(a.b)
#    check(b)
#    