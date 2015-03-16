from builders import graph_utils
from builders.logger import logger
from builders.modifiers import DataIndependentModifier, \
    DataDependentModifier
from inspect import getmembers
import collections
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
        self.clazzToBuild = clazzToBuild
        self.modifiers = []
        self.extra_modifiers = []
        self.result_object = None
        self.class_graph = None
        self.obj_graph = None

    def _build(self, class_graph=None, object_graph=None, extra_subtree_modifiers=None):
        from builders.model_graph import Link, m_graph
        assert (class_graph is not None and object_graph is not None) or (class_graph is None and object_graph is None), "You must either specify both class graph and object graph, or none of them!"
        self.class_graph = class_graph or graph_utils.get_new_classgraph(m_graph, for_class_to_build=self.clazzToBuild)
        self.obj_graph = object_graph or graph_utils.get_clean_graph()

        is_first_run = lambda: class_graph is None and object_graph is None

        self._apply_data_independent_mods(is_first_run())
        
        self._apply_class_mods()
        
        self.result_object = self.clazzToBuild()
        self.obj_graph.add_node(self.result_object)

        for link in self.class_graph.out_edges([self.clazzToBuild], keys=True, data=True):
            lnk = Link(*link, graph=self.class_graph)
            lnk.from_n = self.result_object
            #remember extra modifiers here, because we take backlink and put from_n there as value,though it can have OneOf for example...
            #Handle carefully!
            lnk.create_object(self.modifiers, self.obj_graph, extra_subtree_modifiers)

        self._make_value_constructs()
        self._apply_instance_mods()
        
        if is_first_run():
            self._graph_to_real_model()
        self._apply_data_dependent_mods(is_first_run())

        self.result_object.__object_graph__ = self.obj_graph
        return self.result_object

    def _make_value_constructs(self):
        import construct as construct
        for name, construct in getmembers(self.result_object, lambda x: isinstance(x, construct.ValueConstruct)):
            setattr(self.result_object, name, construct.build(self.modifiers, instance=self.result_object))

    def _graph_to_real_model(self):
        from builders.model_graph import Link
        import construct as construct
        for instance in self.obj_graph.nodes():
            for attr, constr in getmembers(instance, lambda x: isinstance(x, construct.Construct)):
                links = graph_utils.get_out_edges_by_(self.obj_graph, instance, dct={"construct": constr})
                if not links:
                    setattr(instance, attr, None)
                    continue
                for l in links:
                    link = Link(*l)
                    if isinstance(link.get_construct(), construct.Collection):
                        if not isinstance(getattr(instance, attr), list):
                            setattr(instance, attr, [])
                        getattr(instance, attr).append(link.destination())
                    else:                    
                        setattr(instance, attr, link.destination())

    def _get_extra_mods(self):
        node_mods = self.class_graph.node[self.clazzToBuild]["extra_mods"]
        mods = node_mods[0] if node_mods else []
        self.class_graph.node[self.clazzToBuild]["extra_mods"] = tuple(list(node_mods)[1:])
        return mods

    def _apply_instance_mods(self):
        # include valueconstr mod here???
        [m.apply(instance=self.result_object) for m in self.modifiers if m.shouldRun(instance=self.result_object)]

    def _apply_class_mods(self):
        [m.apply(clazz=self.clazzToBuild) for m in self.modifiers if m.shouldRun(clazz=self.clazzToBuild)]

    def _apply_graph_mods(self, is_first_run, class_graph=None, object_graph=None):
        from builders.model_graph import Link
        mods_to_apply = []
        if is_first_run:
            default_mods = list(flatten([Link(edge[0], edge[1], None, edge[2]).get_construct().getDefaultModifiers() for edge in self.class_graph.edges(data=True)]))
            mods_to_apply = default_mods + self.modifiers
            graph_utils.remove_node_unconnected_components(class_graph or object_graph, self.clazzToBuild if class_graph else self.result_object)
            [m.apply(class_graph=class_graph, object_graph=object_graph) for m in mods_to_apply if m.shouldRun(class_graph=class_graph, object_graph=object_graph)]
        
        if not self.extra_modifiers:
            self.extra_modifiers = self._get_extra_mods()
            self.modifiers += self.extra_modifiers
        [m.apply(class_graph=class_graph, object_graph=object_graph) for m in self.extra_modifiers if m.shouldRun(class_graph=class_graph, object_graph=object_graph)]


    def _apply_data_independent_mods(self, is_first_run):
        self._apply_graph_mods(is_first_run, class_graph=self.class_graph)
        #graph_utils.remove_node_unconnected_components(self.class_graph, self.clazzToBuild)

    def _apply_data_dependent_mods(self, is_first_run):
        self._apply_graph_mods(is_first_run, object_graph=self.obj_graph)
        #graph_utils.remove_node_unconnected_components(self.obj_graph, self.result_object)

    def build(self):
        return self._build()

    def withA(self, *modifiers):
        modifiers = flatten(modifiers)
        for mod in modifiers:
            try:
                self.modifiers += list(mod)
            except:
                self.modifiers.append(mod)
        return self


