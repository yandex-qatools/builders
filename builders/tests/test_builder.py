from builders.builder import Builder, flatten
from builders.construct import Unique, Collection, Reused
from builders.modifiers import InstanceModifier


class A:
    b = 0


class B:
    a = Unique(A)
    value = 0


class C:
    b = Unique(B)


def test_single():
    assert isinstance(Builder(A).build(), A)


def test_simple_chain():
    built = Builder(B).build()
    assert isinstance(built.a, A)


def test_longer_chain():
    built = Builder(C).build()
    assert isinstance(built.b.a, A)
    assert isinstance(built.b, B)
    assert isinstance(built, C)


def test_simple_setter():
    modifier = InstanceModifier(B).thatDoes(lambda b: setattr(b, 'value', 1))

    built = Builder(B).withA(modifier).build()
    assert built.value == 1


class D:
    bs = Collection(B)


def test_collection():
    d = Builder(D).build()

    assert d.bs
    assert len(d.bs) == 1
    assert isinstance(d.bs[0], B)


def test_modifier_over_collection():
    modifier = InstanceModifier(B).thatDoes(lambda b: setattr(b, 'value', 8))
    d = Builder(D).withA(modifier).build()

    for b in d.bs:
        assert b.value == 8


class U:
    a = Reused(A, local=True)
    b = Reused(A, local=True)


class V:
    u = Unique(U)


def test_local_reused():
    u1 = Builder(U).build()
    u2 = Builder(U).build()

    assert isinstance(u1.a, A)
    assert isinstance(u1.b, A)
    assert u1.a == u2.a
    assert u1.a != u1.b


def test_local_reused_again():
    v1 = Builder(V).build()
    v2 = Builder(V).build()

    assert isinstance(v1.u.a, A)
    assert v1.u.a == v2.u.a


class R:
    a = Reused(A)
    b = Reused(A)


def test_global_reused():
    r = Builder(R).build()

    assert isinstance(r.a, A)
    assert isinstance(r.a, A)
    assert r.a == r.b


class ReusingKey:
    a = Reused(A, keys=['b'])
    b = Reused(A, keys=['b'])


def test_reused_keys_simple():
    rk = Builder(ReusingKey).build()

    assert isinstance(rk.a, A)
    assert isinstance(rk.b, A)
    assert rk.a == rk.b


def test_reused_keys_mod():
    builder = Builder(ReusingKey).withA(InstanceModifier(A).thatSets(b='ololo'))
    rk1 = builder.build()
    rk2 = builder.build()
    rk3 = builder.withA(InstanceModifier(A).thatSets(b='hahaha')).build()

    assert isinstance(rk1.a, A)
    assert isinstance(rk2.a, A)
    assert isinstance(rk3.a, A)
    assert rk1.a == rk2.a
    assert rk1.b == rk2.b
    assert rk1.a != rk3.a


def test_simple_inheritance():
    class A:
        pass

    class B:
        a = Unique(A)

    class C(B):
        pass

    c = Builder(C).build()
    assert c.a
    assert isinstance(c.a, A)


def test_modifier_supply():
    class A:
        foo = 0
        bar = 0

    class B:
        a = Unique(A)

    mod1 = InstanceModifier(A).thatSets(foo=1)
    mod2 = InstanceModifier(A).thatSets(bar=1)

    b1 = Builder(B).withA(mod1, mod2).build()
    b2 = Builder(B).withA([mod1, mod2]).build()
    b3 = Builder(B).withA(*[mod1, mod2]).build()
    b4 = Builder(B).withA([mod1], [mod2]).build()
    b5 = Builder(B).withA([mod1], mod2).build()

    def test(b):
        assert b.a.foo == 1
        assert b.a.bar == 1

    test(b1)
    test(b2)
    test(b3)
    test(b4)
    test(b5)


def test_flatten():
    l = [[1, 2, 3], [4], [[[5]]], 'ololo']

    assert list(flatten(l)) == [1, 2, 3, 4, 5, 'ololo']


def test_flatten_callable():
    def x():
        return [1, 2, 3]
    y = [4, 5, x]

    assert list(flatten(y)) == [4, 5, 1, 2, 3]


def test_new_style_classes():
    class A(object):
        pass

    class B(object):
        a_s = Collection(A)

    b = Builder(B).build()

    assert isinstance(b, B)
    assert isinstance(b, object)
    assert isinstance(b.a_s[0], A)
    assert isinstance(b.a_s[0], object)
