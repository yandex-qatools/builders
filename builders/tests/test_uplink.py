from builders.builder import Builder
from builders.construct import Unique, Uplink, Collection, Reused
from builders.logger import logger
from builders.model_graph import BuilderModelClass
from builders.modifiers import NumberOf, Given, InstanceModifier, More
import logging
import pytest


class A(BuilderModelClass):
    value = 'OK'
    b = Uplink()


class B(BuilderModelClass):
    a = Unique(A, uplink=A.b)


#A.b.linksTo(B, B.a)


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
    class F(BuilderModelClass):
        value = Uplink()

    with pytest.raises(ValueError):
        Builder(F).build()


class X(BuilderModelClass):
    y = Uplink()


class Y(BuilderModelClass):
    x = Unique(X, uplink=X.y)
    z = Uplink()

#X.y.linksTo(Y, Y.x)


class Z(BuilderModelClass):
    y = Unique(Y, uplink=Y.z)


#Y.z.linksTo(Z, Z.y)


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


class D(BuilderModelClass):
    l = Uplink()
    r = Uplink()


class L(BuilderModelClass):
    d = Unique(D, uplink=D.l)


class R(BuilderModelClass):
    d = Unique(D, uplink=D.r)


#D.l.linksTo(L, L.d)
#D.r.linksTo(R, R.d)


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


class Small(BuilderModelClass):
    value = 'Okay'
    big = Uplink()


class Big(BuilderModelClass):
    smalls = Collection(Small, uplink=Small.big)

#Small.big.linksTo(Big, Big.smalls)


def checkBig(big, indexes):
    assert big
    assert isinstance(big, Big)
    assert big.smalls
    for i in indexes:
        assert isinstance(big.smalls[i], Small)
        assert big.smalls[i].big == big


def test_Collection_Uplink():
    checkBig(Builder(Big).build(), range(1))

@pytest.mark.xfail
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


#class Down(BuilderModelClass):
#    up = Uplink(reusing_by=['id'])
#
#
#class Up(BuilderModelClass):
#    id = 0
#    downs = Collection(Down, uplink=Down.up)
#
##Down.up.linksTo(Up, Up.downs)
#
#
#def test_reuse():
#    d1 = Builder(Down).withA(InstanceModifier(Up).thatSets(id=1)).build()
#
#    # assert d1 in d1.up.downs FIXME: this should work
#
#    d2 = Builder(Down).withA(InstanceModifier(Up).thatSets(id=1)).build()
#    d3 = Builder(Down).withA(InstanceModifier(Up).thatSets(id=2)).build()
#
#    assert d1.up == d2.up
#    # assert d1 in d2.up.downs FIXME: this should work
#    # assert d2 in d2.up.downs FIXME: this should work
#    assert d1.up != d3.up
#
#
#def test_reuse_regression():
#    u1 = Builder(Up).withA(NumberOf(Up.downs, 3)).build()
#
#    assert u1.downs[0].up == u1
#    assert u1.downs[1].up == u1
#    assert u1.downs[2].up == u1


def test_uplink_reset():
    class B(BuilderModelClass):
        a = Uplink()

    class A(BuilderModelClass):
        bs = Collection(B, uplink=B.a)

    #B.a.linksTo(A, A.bs)

    a = Builder(A).withA(NumberOf(A.bs, 0)).build()
    b = Builder(B).build()

    assert a != b.a


def test_collection_mid_uplink_aa():
    class A(BuilderModelClass):
        b = Uplink()

    class B(BuilderModelClass):
        aa = Collection(A, uplink=A.b)
        c = Uplink()

    class C(BuilderModelClass):
        bb = Collection(B, uplink=B.c)

    #B.c.linksTo(C, C.bb)
    #A.b.linksTo(B, B.aa)

    c = Builder(B).withA(More(B.aa, 1),
                         More(C.bb, 1)).build().c

    assert len(c.bb) == 2
    assert len(c.bb[0].aa) == 2
    assert len(c.bb[1].aa) == 2


def test_collection_mid_uplink_zaa():
    """
    Same as for ``aa``, but with different naming
    """

    logger.setLevel(logging.DEBUG)

    class A(BuilderModelClass):
        b = Uplink()

    class B(BuilderModelClass):
        zaa = Collection(A, uplink=A.b)
        c = Uplink()

    class C(BuilderModelClass):
        bb = Collection(B, uplink=B.c)

    #B.c.linksTo(C, C.bb)
    #A.b.linksTo(B, B.zaa)

    builder = Builder(B).withA(More(B.zaa, 1),
                               More(C.bb, 1))

    c = builder.build().c

    assert len(c.bb) == 2
    assert len(c.bb[0].zaa) == 2
    assert len(c.bb[1].zaa) == 2


class L2(BuilderModelClass):
    d = Uplink()


class R2(BuilderModelClass):
    d = Uplink()


class D2(BuilderModelClass):
    l = Reused(L2, uplink=L2.d)
    r = Reused(R2, uplink=R2.d)

#L2.d.linksTo(D2, D2.l)
#R2.d.linksTo(D2, D2.r)


@pytest.fixture(scope='function')
def clear_state():
    Reused._Reused__reused_instances.clear()  # XXX: note the name mangling @UndefinedVariable


def test_double_incoming_uplinks(clear_state):
    d = Builder(D2).build()
    assert d.l.d == d
    assert d.r.d == d


def test_double_incoming_uplinks_left_branch(clear_state):
    r = Builder(R2).build()
    assert r.d.r.d == r.d
    assert r.d.l.d == r.d


def test_double_incoming_uplinks_right_branch(clear_state):
    l = Builder(R2).build()
    assert l.d.l.d == l.d
    assert l.d.r.d == l.d
