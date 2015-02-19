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


def count_out_links_by_local_attr(obj_graph, node, attr):
    i = 0
    for from_n, to_n, k, data in m_graph.out_edges([node], keys=True, data=True):
        if data["local_attr"] == attr:
            i+=1
    return i


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
                            m_graph.add_edge(value.type, bmo, attr_dict={"rel_type": relation_types[remote_value.__class__],
                                                                         "local_attr": remote_attr,
                                                                         "remote_attr": attr})
                            remote_attr_found = remote_attr
                            break
                m_graph.add_edge(bmo, value.type, attr_dict={"rel_type": relation_types[value.__class__],
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