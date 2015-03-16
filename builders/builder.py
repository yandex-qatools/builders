from builders import graph_utils
from builders.logger import logger
from builders.model_graph import Many, One, m_graph
from inspect import getmembers
import collections
import construct
import networkx as nx


def flatten(l):
    """
        :arg l: iterable to flatten

        Generator that flattens iterable infinitely. If an item is iterable, ``flatten`` descends on it.
        If it is callable, it descends on the call result (with no arguments), and it yields the item itself otherwise.
    """
    for el in l:
        if isinstance(el, collections.Iterable) and not isinstance(el, basestring):
            for sub in flatten(el):
                yield sub
        elif callable(el):
            for sub in flatten(el()):
                yield sub
        else:
            yield el


class Builder:
    def __init__(self, clazzToBuild):
        self.class_to_build = clazzToBuild
        self.modifiers = []
        self.result_object = None

        self.class_graph = None
        self.obj_graph = None
        
    def _build_default_graph(self):
        self.class_graph = graph_utils.get_new_classgraph(for_class_to_build=self.class_to_build)
        self.obj_graph = graph_utils.get_clean_graph()
        self.result_object = self._build_element(self.class_to_build)

    def _build_element(self, class_to_build=None, construct=None):
        element = class_to_build()
        element.__object_graph__ = self.obj_graph
        self.obj_graph.add_node(element)
        self.class_graph.node[class_to_build]["instances"] = [inst for inst in self.class_graph.node[class_to_build]["instances"]] + [element]
        for link in class_out_edges(even Uplink):
            for link.construct.amount:
                linked_el = self._build_element(link[1])
                self.obj_graph.add_edge(el, l_el, data=link[-1])
                link_back_if_possible
            

    def build(self, with_graph=False, do_finalize=True):
        pass

    def withA(self, *modifiers):
        modifiers = flatten(modifiers)
        for mod in modifiers:
            try:
                self.modifiers += list(mod)
            except:
                self.modifiers.append(mod)
        return self


class ABuilder:
    def __init__(self, clazzToBuild):
        self.class_graph = None
        self.clazz = clazzToBuild
        self.modifiers = []
        self.obj_graph = None
        self.result_object = None

    def _buildclazz(self, clazzToBuild, do_finalize=True):
        self._build_default_obj_graph()
        self._apply_graph_modifiers()
        if do_finalize:
            self._finalize_objects_structure()
        #self._apply_instance_modifiers()
        return self.result_object

    def _build_default_obj_graph(self):
        import model_graph
        import model_graph as graph_utils
        self.class_graph = graph_utils.nondeepcopy_graph(model_graph.m_graph)
        graph_utils.remove_node_unconnected_components(self.class_graph, self.clazz)
        
        mapping = {clazz: clazz() for clazz in self.class_graph.nodes()}
        self.obj_graph = graph_utils.nondeepcopy_graph(self.class_graph)
        self.obj_graph = nx.relabel_nodes(self.obj_graph, mapping)
        self.result_object = mapping[self.clazz]

        self.obj_graph.add_nodes_from(self.class_graph.nodes(data=True))
        #self.obj_graph.add_edges_from(self.class_graph.edges(data=True))
        for clazz, instance in mapping.items():
            self.obj_graph.add_edge(clazz, instance)
            self.obj_graph.add_edge(instance, clazz)
        return self.obj_graph

    def _apply_graph_modifiers(self):
        for m in self.modifiers:
            if m.shouldRun(obj_graph=self.obj_graph):
                m.apply(obj_graph=self.obj_graph, modifiers=self.modifiers)
    
    def _apply_instance_modifiers(self, instance):
        for m in self.modifiers:
            if m.shouldRun(instance=instance):
                m.apply(instance=instance)

    def _finalize_objects_structure(self):
        import model_graph as graph_utils
        graph_utils.remove_node_unconnected_components(self.obj_graph, self.result_object, exclude_nodes=self.class_graph.nodes())
        for instance in self.obj_graph.nodes():
            if instance in self.class_graph.nodes():
                continue
            for _, to_instance, link_data in self.obj_graph.out_edges([instance], data=True):
                if to_instance in self.class_graph.nodes():
                    continue
                if link_data["rel_type"] == Many:
                    if not isinstance(getattr(instance, link_data["local_attr"]), list):
                        setattr(instance, link_data["local_attr"], [])
                    getattr(instance, link_data["local_attr"]).append(to_instance)
                elif link_data["rel_type"] == One:                    
                    setattr(instance, link_data["local_attr"], to_instance)

            for attr, constr in getmembers(instance, lambda x: isinstance(x, construct.ValueConstruct)):
                setattr(instance, attr, constr.doBuild([], instance=instance))

            self._apply_instance_modifiers(instance)
            instance.__object_graph__ = self.obj_graph


    def build(self, with_graph=False, do_finalize=True):
        if with_graph:
            return (self._buildclazz(self.clazz, do_finalize=do_finalize), self.obj_graph)
        else:
            return self._buildclazz(self.clazz)

    def withA(self, *modifiers):
        modifiers = flatten(modifiers)
        for mod in modifiers:
            try:
                self.modifiers += list(mod)
            except:
                self.modifiers.append(mod)
        return self

