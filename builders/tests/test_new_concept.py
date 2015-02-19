from builders.builder import Builder
from builders.construct import Unique, Uplink, Collection
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

g = Builder(A).withA(NumberOf(A.b, 2)).build()'''

class A(BuilderModelClass):
    value = 'OK'
    b = Uplink()


class B(BuilderModelClass):
    a = Unique(A)


A.b.linksTo(B, B.a)


print m_graph.nodes()
print m_graph.edges(data=True)


b = Builder(B).build()
assert isinstance(b, B)
assert isinstance(b.a, A)
assert isinstance(b.a.b, B)
assert b == b.a.b

assert not A.b.value
assert not B.a.value

print 1
