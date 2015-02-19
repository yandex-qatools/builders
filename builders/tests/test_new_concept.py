from builders.builder import Builder
from builders.construct import Unique, Uplink, Collection
from builders.model_graph import BuilderModelClass, m_graph
import networkx as nx



class B(BuilderModelClass):
    a = Uplink(links_to="A.b")
    c = Uplink(links_to="C.b")


class A(BuilderModelClass):
    b = Collection(B)


class C(BuilderModelClass):
    b = Collection(B)


print m_graph.nodes()
print m_graph.edges(data=True)

g = Builder(A).withA(NumberOf(A.b, 3)).build()


#print g.nodes(data=True)
#print g.edges(data=True)
