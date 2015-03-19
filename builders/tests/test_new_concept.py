from builders.builder import Builder
from builders.construct import Maybe, Unique, Uplink, Collection, Reused
from builders.model_graph import BuilderModelClass
from builders.modifiers import Enabled, NumberOf, More, OneOf, InstanceModifier
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
            if "extra_mods" in link.keys():
                link["extra_mods"] = [str(x) for x in link["extra_mods"]]
        js = json.dumps(d)
        
        with open(DEST_FILE, "w") as result:
            result.write(html % js)


class A(BuilderModelClass):
    a = 0
    b = Uplink()

class B(BuilderModelClass):
    #values = Collection(A, uplink=A.b)
    v = 0
    c = Uplink()

class C(BuilderModelClass):
    values = Collection(B, uplink=B.c)

#A.b.linksTo(B, B.values)

def test():
    b = Builder(B).withA(NumberOf(C.values, 2), OneOf(C.values, InstanceModifier(B).thatSets(v=1)), OneOf(C.values, InstanceModifier(B).thatSets(v=2))).build()
        #withA(OneOf(C.values, NumberOf(B.values, 2), OneOf(B.values, InstanceModifier(A).thatSets(a=2)))).\
        #build()
    
    c = b.c
    assert len(c.values) == 2
    assert len([v for v in c.values if v.v == 0]) == 1
    assert len([v for v in c.values if v.v == 1]) == 1
#    assert c.values[0] != c.values[1]
#    assert len(c.values[0].values) == 1 and len(c.values[1].values) == 1
#    assert c.values[0].values[0] != c.values[1].values[0]
    return c

#pp.pprint(u1.__object_graph__.nodes())
#pp.pprint(u1.__object_graph__.edges(data=True))
draw(test())



#print m_graph.nodes()
#print m_graph.edges(data=True)

print 1

