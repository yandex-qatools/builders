import networkx as nx


def get_new_classgraph(ethalon_graph, for_class_to_build=None):
    g = nondeepcopy_graph(ethalon_graph)
    if for_class_to_build is not None:
        remove_node_unconnected_components(g, for_class_to_build)
    return g

def get_clean_graph():
    return nx.MultiDiGraph()

def nondeepcopy_graph(graph):
    new_g = nx.MultiDiGraph()
    new_g.add_nodes_from(graph.nodes(data=True))
    new_g.add_edges_from(graph.edges(data=True))
    return new_g

def replace_graph(source, target):
    target.clear()
    target.add_nodes_from(source.nodes(data=True))
    target.add_edges_from(source.edges(data=True))

def get_out_edges_by_(obj_graph, node=None, link_attr="construct", value=None, dct=None):
    if not dct:
        return get_edges_by_(obj_graph, node, dct={link_attr: value}, edges_get_func=obj_graph.out_edges)
    else:
        return get_edges_by_(obj_graph, node, dct=dct, edges_get_func=obj_graph.out_edges)


def get_in_edges_by_(obj_graph, node=None, link_attr="construct", value=None, dct=None):
    if not dct:
        return get_edges_by_(obj_graph, node, dct={link_attr: value}, edges_get_func=obj_graph.in_edges)
    else:
        return get_edges_by_(obj_graph, node, dct=dct, edges_get_func=obj_graph.in_edges)


def get_edges_by_(obj_graph, node=None, dct=None, edges_get_func=None):
    edges = []
    nodes = [node] if node is not None else None
    for edge in edges_get_func(nodes, keys=True, data=True):
        data = edge[-1]
        if len(dct.items()) == len([k for k in dct.keys() if dct[k] == data[k]]):
            edges.append(edge)
    return edges


#def link_instance_nodes(obj_graph, n1, n2):
#    edges = m_graph.edges([n1.__class__, n2.__class__], data=True)
#    for from_n, to_n, data in edges:
#        if (from_n == n1.__class__ and to_n == n2.__class__):
#            obj_graph.add_edge(n1, n2, attr_dict=data)
#        elif (from_n == n2.__class__ and to_n == n1.__class__):
#            obj_graph.add_edge(n2, n1, attr_dict=data)


def remove_node_unconnected_components(graph, node, exclude_nodes=()):
    com = None
    if exclude_nodes:
        copy_g = nondeepcopy_graph(graph)
        copy_g.remove_nodes_from(exclude_nodes)
        com = nx.node_connected_component(copy_g.to_undirected(), node)
    else:
        com = nx.node_connected_component(graph.to_undirected(), node)
    for n in graph.nodes():
        if n not in com + list(exclude_nodes):
            graph.remove_node(n)