from builders.builder import Builder
from builders.construct import Unique, Uplink, Collection, Key, Random, Lambda
from builders.model_graph import BuilderModelClass, m_graph
from builders.modifiers import NumberOf
import networkx as nx

'''
class B(BuilderModelClass):
    a = Uplink(links_to="A.b")
    c = Uplink(links_to="C.b")


class A(BuilderModelClass):
    b = Collection(B)


class C(BuilderModelClass):
    b = Collection(B)


print m_graph.nodes()
print m_graph.edges(data=True)

a = Builder(A).withA(NumberOf(A.b, 2)).build()

assert len(a.b) == 2
assert a.b[0].a == a.b[1].a and a.b[0].a == a
assert a.b[0].c != a.b[1].c
assert len(a.b[0].c.b) == 1 and len(a.b[1].c.b) == 1
assert a.b[0].c.b[0].c == a.b[0].c and a.b[1].c.b[0].c == a.b[1].c
'''

'''
class A(BuilderModelClass):
    value = 'OK'
    b = Uplink()


class B(BuilderModelClass):
    a = Unique(A)


A.b.linksTo(B, B.a)

b = Builder(B).build()
assert isinstance(b, B)
assert isinstance(b.a, A)
assert isinstance(b.a.b, B)
assert b == b.a.b

assert not A.b.value
assert not B.a.value
'''

def test_key_is_unique():
    class A(BuilderModelClass):
        a = Key(Random(start=1, end=3))

    values = [Builder(A).build().a for _ in xrange(3)]

    assert sorted(list(set(values))) == sorted(values)


def test_lambda_executed_twice():
    from itertools import count
    gen = count()

    class A(BuilderModelClass):
        a = Lambda(lambda _: gen.next())

    values = [Builder(A).build().a for _ in xrange(2)]

    assert (values[0], values[1]) == (0, 1)


print m_graph.nodes()
print m_graph.edges(data=True)

print 1
