from builders.model_graph import BuilderModelClass
from builders.builder import Builder
from builders.construct import Maybe, Unique, Uplink, Collection, Reused
from builders.modifiers import Enabled, NumberOf, More, OneOf
from networkx.readwrite import json_graph
import builders.tests.drawer
import json
import networkx as nx
import os
import pprint

pp = pprint.PrettyPrinter(indent=2)

TEMPLATE_FILE = os.path.join(os.path.dirname(builders.tests.drawer.__file__), 'template.html')
DEST_FILE = os.path.join(os.path.dirname(builders.tests.__file__), 'graph.html')

def draw(obj):
    from builders.graph_utils import nondeepcopy_graph
    with open(TEMPLATE_FILE, 'r') as template:
        html = template.read()
        gr = nondeepcopy_graph(obj.__object_graph__)
        #gr.remove_nodes_from(m_graph.nodes())
        d = json_graph.node_link_data(gr)
        for node in d["nodes"]:
            node["id"] = str(node["id"])
        for link in d["links"]:
            if "construct" in link.keys():
                link["construct"] = str(link["construct"])
            if "uplink_for" in link.keys():
                link["uplink_for"] = str(link["uplink_for"])
            if "instance" in link.keys():
                link["instance"] = str(link["instance"])
            if "visited_from" in link.keys():
                link["visited_from"] = [str(x) for x in link["visited_from"]]
        js = json.dumps(d)
        
        with open(DEST_FILE, "w") as result:
            result.write(html % js)


class D3(BuilderModelClass):
    d2 = Uplink()


class D2(BuilderModelClass):
    d1 = Uplink()
    d3 = Collection(D3, uplink=D3.d2)


class D1(BuilderModelClass):
    d2 = Collection(D2, uplink=D2.d1)


d = Builder(D3).withA(NumberOf(D1.d2, 2), OneOf(D1.d2, NumberOf(D2.d3, 2))).build()

#pp.pprint(u1.__object_graph__.nodes())
#pp.pprint(u1.__object_graph__.edges(data=True))
draw(d)

'''
class A(BuilderModelClass):
        b = Uplink()

class B(BuilderModelClass):
    zaa = Collection(A)
    c = Uplink()

class C(BuilderModelClass):
    bb = Collection(B)

B.c.linksTo(C, C.bb)
A.b.linksTo(B, B.zaa)

builder = Builder(B).withA(HavingIn(B.zaa, 1),
                           HavingIn(C.bb, 1))

b = builder.build()
c = b.c


print b.__object_graph__.nodes()
print b.__object_graph__.edges(data=True)
draw(b)

assert len(c.bb) == 2
assert len(c.bb[0].zaa) == 2
assert len(c.bb[1].zaa) == 2
'''

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

draw(a)

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
'''

#print m_graph.nodes()
#print m_graph.edges(data=True)

print 1

