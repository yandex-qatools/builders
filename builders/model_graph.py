from builders import graph_utils
import inspect
import networkx as nx
import construct as construct

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


class Link(object):
    def __init__(self, from_n, to_n, key, data, graph=None):
        self.from_n = from_n
        self.to_n = to_n
        self.key = key
        self.data = data
        self.graph = graph

    def create_object(self, modifiers, object_graph, from_obj):
        #TODO: remember Maybe must remove edges if disabled!!!
        #import graph_utils
        if from_obj in self.data["visited_from"]:
            return

        self.data["visited_from"] = tuple(list(self.data["visited_from"]) + [from_obj])
        
        result = None
        if self.has_object():
            result = self.get_instance()
            self.clear_instance()
        else:
            backlink = None
            if self.is_uplink():
                main_links = graph_utils.get_out_edges_by_(self.graph, node=self.to_n, dct={"construct": self.uplink_for()})
                assert main_links, "Uplink is broken: can't find free main link"
                backlink = main_links[0]   
            else:
                uplinks = graph_utils.get_out_edges_by_(self.graph, node=self.to_n, dct={"uplink_for": self.get_construct()})
                assert len(uplinks) <= 1, "Found more than 1 uplink for 1 construct!"
                if uplinks:
                    backlink = uplinks[0]
            
            if backlink:
                backlink[-1]["instance"] = from_obj
    
            #remember extra modifiers here, because we take backlink and put from_n there as value,though it can have OneOf for example...
            #Handle carefully!
            result = self.get_construct().build(modifiers, self.graph, object_graph)

        if not result:
            return 

        self.from_n = from_obj
        self.to_n = result
        self.add_to(object_graph)

    def source(self):
        return self.from_n

    def source_attr(self):
        return self.data["local_attr"]

    def get_visited_from(self):
        return self.data["visited_from"]

    def get_construct(self):
        return self.data["construct"]

    def get_instance(self):
        return self.data["instance"]

    def clear_instance(self):
        self.data["instance"] = None

    def is_uplink(self):
        return isinstance(self.get_construct(), construct.Uplink)
    
    def uplink_for(self):
        return self.get_construct().getLinkDestination()[0]

    def has_object(self):
        return self.get_instance() is not None

    def add(self):
        self.graph.add_edge(self.from_n, self.to_n, attr_dict=self.data)

    def add_to(self, graph):
        self.graph = graph
        self.key = None
        self.add()

    def remove(self):
        self.graph.remove_edge(self.from_n, self.to_n, self.key)

    def remove_destination(self):
        self.graph.remove_node(self.to_n)
        self.to_n = None

    def destination(self):
        return self.to_n

    def extra_modifiers(self):
        return []

#Builder Model Class metaclass
class BMCMeta(type):
    def __new__(cls, clsname, bases, dct):

        bmo = super(BMCMeta, cls).__new__(cls, clsname, bases, dct)
        
        if clsname == "BuilderModelClass":
            return bmo
        
        m_graph.add_node(bmo, attr_dict={"extra_mods": ()})

        for attr, value in inspect.getmembers(bmo):
            if not isinstance(value, construct.Construct) or value.__class__ not in relation_types.keys():
                continue
            if not isinstance(value, construct.Uplink):
                remote_attr_found = None
                for remote_attr, remote_value in value.type.__dict__.items():
                    if isinstance(remote_value, construct.Uplink):
                        dest_construct, dest_type = remote_value.getLinkDestination()
                        if dest_construct == value or isinstance(value, construct.Maybe) and value.construct == dest_construct:
                            assert dest_type is None, "Uplink is being initiated the second time!"
                            remote_value.setDestination(remote_construct = value, type_to_build = bmo)
                            m_graph.add_edge(value.getTypeToBuild(), bmo, attr_dict={"construct": remote_value,
                                                                                     "local_attr": remote_attr,
                                                                                     "remote_attr": attr,
                                                                                     "uplink_for": dest_construct,
                                                                                     "visited_from": (),
                                                                                     "instance": None})
                            remote_attr_found = remote_attr
                            break
                m_graph.add_edge(bmo, value.type, attr_dict={"construct": value,
                                                             "local_attr": attr,
                                                             "remote_attr": remote_attr_found,
                                                             "uplink_for": None,
                                                             "visited_from": (),
                                                             "instance": None})

        return bmo


class BuilderModelClass(object):
    __metaclass__ = BMCMeta
    __object_graph__ = None
    
    def _get_field_by_value(self, value):
        for k, v in self.__dict__.items():
            if v == value:
                return k
        return None