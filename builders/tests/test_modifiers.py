from builders.construct import Unique, Collection, Uplink, Maybe, Lambda, Random
from builders.modifiers import Given, InstanceModifier, NumberOf, HavingIn, \
    OneOf, Enabled, ValuesMixin, LambdaModifier
from builders.builder import Builder
import pytest


class A:
    value = 1


class B:
    a = Unique(A)


class C:
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
    class A:
        pass

    class B:
        a = Unique(A)

    b1 = Builder(B).withA(Given(B.a, 8)).build()
    assert b1.a == 8

    b2 = Builder(B).build()

    assert isinstance(b2.a, A)


def test_modifies_dont_affect_given():
    class A:
        value = 0

    class B:
        a = Unique(A)

    myA = A()
    myA.value = 1

    b = Builder(B).withA(Given(B.a, myA)).withA(InstanceModifier(A).thatSets(value=5)).build()

    assert b.a.value == 1
    assert b.a == myA


def test_having():
    class A:
        pass

    class B:
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
    class A:
        pass

    class B:
        a = Collection(A)

    myA = A()
    b = Builder(B).withA(HavingIn(B.a, myA)).build()

    assert myA in b.a

    b2 = Builder(B).withA(HavingIn(B.a, myA)).withA(NumberOf(B.a, 3)).build()
    assert myA in b2.a
    assert len(b2.a) == 3


def test_thatSets():
    class A:
        pass

    a = Builder(A).withA(InstanceModifier(A).thatSets(ololo=1, hahaha=2)).build()
    assert a.ololo == 1
    assert a.hahaha == 2


def test_one_of():
    class A:
        a = 0
        b = Uplink()

    class B:
        values = Collection(A)

    A.b.linksTo(B, B.values)

    b = Builder(B).withA(NumberOf(B.values, 3)).\
        withA(OneOf(B.values, InstanceModifier(A).thatSets(a=8))).\
        withA(OneOf(B.values, InstanceModifier(A).thatSets(a=5))).\
        build()

    assert len(b.values) == 3
    assert len([a for a in b.values if a.a == 8]) == 1
    assert len([a for a in b.values if a.a == 5]) == 1


def test_maybe():
    class A:
        b = Uplink()

    class B:
        a = Maybe(Unique(A))

    A.b.linksTo(B, B.a)

    b1 = Builder(B).build()
    b2 = Builder(B).withA(Enabled(B.a)).build()
    a = Builder(A).withA(Enabled(B.a)).build()

    assert not b1.a
    assert isinstance(b2.a, A)
    assert b2.a.b == b2
    assert a.b.a == a


class CarefulA:
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
    class A:
        a = Lambda(lambda _: 1)

    assert Builder(A).withA(LambdaModifier(A.a, lambda _: 2)).build().a == 2


def test_lambda_modifier_function_is_set_back():
    class A:
        a = Lambda(lambda _: 1)

    Builder(A).withA(LambdaModifier(A.a, lambda _: 2)).build()
    assert Builder(A).build().a == 1


def test_lambda_modifier_raises_given_not_lambda():
    class A:
        a = Random()

    with pytest.raises(TypeError):
        Builder(A).withA(LambdaModifier(A.a, lambda _: 2)).build()


class Foo(ValuesMixin):
        bar = 0
        baz = ''


def test_values_mixin(monkeypatch):
    assert Builder(Foo).withA(Foo.values(bar=1)).build().bar == 1
    assert Builder(Foo).withA(Foo.values(baz='baz')).build().baz == 'baz'
