from builders.construct import Unique, Uplink, Collection
from builders.modifiers import NumberOf, Given, InstanceModifier, HavingIn
from builders.builder import Builder
import pytest


class A:
    value = 'OK'
    b = Uplink()


class B:
    a = Unique(A)


A.b.linksTo(B, B.a)


def test_simple():
    b = Builder(B).build()
    assert isinstance(b, B)
    assert isinstance(b.a, A)
    assert isinstance(b.a.b, B)
    assert b == b.a.b

    assert not A.b.value
    assert not B.a.value


def test_reverse():
    a = Builder(A).build()

    assert isinstance(a, A)
    assert isinstance(a.b, B)
    assert isinstance(a.b.a, A)
    assert a == a.b.a

    assert not A.b.value
    assert not B.a.value


def test_unlinked():
    class F:
        value = Uplink()

    with pytest.raises(ValueError):
        Builder(F).build()


class X:
    y = Uplink()


class Y:
    x = Unique(X)
    z = Uplink()

X.y.linksTo(Y, Y.x)


class Z:
    y = Unique(Y)


Y.z.linksTo(Z, Z.y)


def test_long_chain():
    z = Builder(Z).build()

    assert z
    assert isinstance(z, Z)
    assert isinstance(z.y, Y)
    assert isinstance(z.y.x, X)
    assert z == z.y.z
    assert z.y.x.y == z.y
    assert z.y.x.y.z == z

    assert not X.y.value
    assert not Y.x.value
    assert not Y.z.value
    assert not Z.y.value


def test_long_chain_reverse():
    x = Builder(X).build()

    assert x
    assert isinstance(x, X)
    assert isinstance(x.y, Y)
    assert isinstance(x.y.z, Z)
    assert x == x.y.x
    assert x.y.z.y == x.y
    assert x.y.z.y.x == x

    assert not X.y.value
    assert not Y.x.value
    assert not Y.z.value
    assert not Z.y.value


class D:
    l = Uplink()
    r = Uplink()


class L:
    d = Unique(D)


class R:
    d = Unique(D)


D.l.linksTo(L, L.d)
D.r.linksTo(R, R.d)


def test_Y():
    r = Builder(R).build()
    assert r
    assert isinstance(r, R)
    assert isinstance(r.d, D)
    assert isinstance(r.d.l, L)
    assert r.d.r == r
    assert r.d.l.d == r.d

    assert not D.r.value
    assert not D.l.value


def test_Y_reverse():
    d = Builder(D).build()

    assert d
    assert isinstance(d, D)
    assert isinstance(d.r, R)
    assert isinstance(d.l, L)
    assert d.l.d == d
    assert d.r.d == d


def test_Given():
    b = Builder(B).withA(Given(B.a, 8)).build()

    assert b
    assert b.a == 8


class Small:
    value = 'Okay'
    big = Uplink()


class Big:
    smalls = Collection(Small)

Small.big.linksTo(Big, Big.smalls)


def checkBig(big, indexes):
    assert big
    assert isinstance(big, Big)
    assert big.smalls
    for i in indexes:
        assert isinstance(big.smalls[i], Small)
        assert big.smalls[i].big == big


def test_Collection_Uplink():
    checkBig(Builder(Big).build(), range(1))


def test_Collection_with_set_number():
    Big.smalls.number = 2
    checkBig(Builder(Big).build(), range(2))


def test_Collection_with_number_Uplink():
    Big.smalls.number = 1
    checkBig(Builder(Big).withA(NumberOf(Big.smalls, 2)).build(), range(2))


@pytest.mark.parametrize(('number'), [1, 2, 3])
def test_collection_from_bottom(number):
    small = Builder(Small).withA(NumberOf(Big.smalls, number)).build()
    assert small
    assert isinstance(small, Small)
    assert small.big
    assert isinstance(small.big, Big)
    assert small.big.smalls
    assert len(small.big.smalls) == number
    for s in small.big.smalls:
        assert s
        assert s in small.big.smalls
        assert isinstance(s.big, Big)
        assert s.big == small.big


class Down:
    up = Uplink(reusing_by=['id'])


class Up:
    id = 0
    downs = Collection(Down)

Down.up.linksTo(Up, Up.downs)


def test_reuse():
    d1 = Builder(Down).withA(InstanceModifier(Up).thatSets(id=1)).build()

    # assert d1 in d1.up.downs FIXME: this should work

    d2 = Builder(Down).withA(InstanceModifier(Up).thatSets(id=1)).build()
    d3 = Builder(Down).withA(InstanceModifier(Up).thatSets(id=2)).build()

    assert d1.up == d2.up
    # assert d1 in d2.up.downs FIXME: this should work
    # assert d2 in d2.up.downs FIXME: this should work
    assert d1.up != d3.up


def test_reuse_regression():
    u1 = Builder(Up).withA(NumberOf(Up.downs, 3)).build()

    assert u1.downs[0].up == u1
    assert u1.downs[1].up == u1
    assert u1.downs[2].up == u1


def test_uplink_reset():
    class B:
        a = Uplink()

    class A:
        bs = Collection(B)

    B.a.linksTo(A, A.bs)

    a = Builder(A).withA(NumberOf(A.bs, 0)).build()
    b = Builder(B).build()

    assert a != b.a


def test_collection_mid_uplink_aa():
    class A:
        b = Uplink()

    class B:
        aa = Collection(A)
        c = Uplink()

    class C:
        bb = Collection(B)

    B.c.linksTo(C, C.bb)
    A.b.linksTo(B, B.aa)

    c = Builder(B).withA(HavingIn(B.aa, 1),
                         HavingIn(C.bb, 1)).build().c

    assert len(c.bb) == 2
    assert len(c.bb[0].aa) == 2
    assert len(c.bb[1].aa) == 2


def test_collection_mid_uplink_zaa():
    """
    Same as for ``aa``, but with different naming
    """
    class A:
        b = Uplink()

    class B:
        zaa = Collection(A)
        c = Uplink()

    class C:
        bb = Collection(B)

    B.c.linksTo(C, C.bb)
    A.b.linksTo(B, B.zaa)

    c = Builder(B).withA(HavingIn(B.zaa, 1),
                         HavingIn(C.bb, 1)).build().c

    assert len(c.bb) == 2
    assert len(c.bb[0].zaa) == 2
    assert len(c.bb[1].zaa) == 2
