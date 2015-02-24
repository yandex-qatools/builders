import construct
import networkx as nx

#relation types
#TODO: use enum34
Many = "many"
One = "one"
Undefined = "undef"

m_graph = nx.MultiDiGraph()
relation_base = construct.Construct
relation_types = {
                  construct.Collection: Many,
                  construct.Unique: One, 
                  construct.Reused: One,
                  construct.Uplink: One,
                  construct.Maybe: Undefined,
                  }


def nondeepcopy_graph(graph):
    new_g = nx.MultiDiGraph()
    new_g.add_nodes_from(graph.nodes(data=True))
    new_g.add_edges_from(graph.edges(data=True))
    return new_g


def get_out_edges_by_(obj_graph, node=None, link_attr="construct", value=None):
    edges = []
    nodes = [node] if node is not None else None
    for out_edge in obj_graph.out_edges(nodes, keys=True, data=True):
        data = out_edge[-1]
        if data and link_attr in data.keys() and data[link_attr] == value:
            edges.append(out_edge)
    return edges


def link_instance_nodes(obj_graph, n1, n2):
    edges = m_graph.edges([n1.__class__, n2.__class__], data=True)
    for from_n, to_n, data in edges:
        if (from_n == n1.__class__ and to_n == n2.__class__):
            obj_graph.add_edge(n1, n2, attr_dict=data)
        elif (from_n == n2.__class__ and to_n == n1.__class__):
            obj_graph.add_edge(n2, n1, attr_dict=data)


def remove_node_unconnected_components(graph, node):
    com = nx.node_connected_component(graph.to_undirected(), node)
    for n in graph.nodes():
        if n not in com:
            graph.remove_node(n)


#Builder Model Class metaclass
class BMCMeta(type):
    def __new__(cls, clsname, bases, dct):
        bmo = super(BMCMeta, cls).__new__(cls, clsname, bases, dct)
        if clsname == "BuilderModelClass":
            return bmo
        
        m_graph.add_node(bmo)
        
        for attr, value in dct.items():
            if not isinstance(value, construct.Construct) or value.__class__ not in relation_types.keys():
                continue
            if isinstance(value,construct.Maybe):
                value = value.construct
            if not isinstance(value, construct.Uplink): 
                remote_attr_found = None
                for remote_attr, remote_value in value.type.__dict__.items():
                    if isinstance(remote_value, construct.Uplink):
                        dest = remote_value.getLinkDestination()
                        if dest is not None and dest["cls"] == clsname and dest["attr"] == attr:
                            m_graph.add_edge(value.type, bmo, attr_dict={"construct": remote_value,
                                                                         "rel_type": relation_types[remote_value.__class__],
                                                                         "local_attr": remote_attr,
                                                                         "remote_attr": attr})
                            remote_attr_found = remote_attr
                            break
                m_graph.add_edge(bmo, value.type, attr_dict={"construct": value,
                                                             "rel_type": relation_types[value.__class__],
                                                             "local_attr": attr,
                                                             "remote_attr": remote_attr_found})

        return bmo


class BuilderModelClass(object):
    __metaclass__ = BMCMeta
    
    def _get_field_by_value(self, value):
        for k, v in self.__dict__.items():
            if v == value:
                return k
        return None