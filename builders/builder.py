from builders.logger import logger
from builders.model_graph import Many, One
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
        import model_graph
        self.class_graph = model_graph.m_graph.copy()
        self.clazz = clazzToBuild
        self.modifiers = []
        self.class_graph = None
        self.obj_graph = None
        

    def _buildclazz(self, clazzToBuild, do_finalize=True):
        self._build_default_obj_graph()
        self._apply_graph_modifiers()
        if do_finalize:
            self._finalize_objects_structure()
        self._apply_instance_modifiers()
        return self.obj_graph.node[(clazzToBuild, 0)]["instance"]

    def _build_default_obj_graph(self):
        mapping = {clazz: (clazz, 0) for clazz in self.class_graph.nodes()}
        print mapping
        self.obj_graph = nx.relabel_nodes(self.class_graph, mapping, copy = True)
        print self.obj_graph.nodes(data=True)
        for node in self.obj_graph.nodes():
            self.obj_graph.node[node]["instance"] = node[0]()
        return self.obj_graph

    def _apply_graph_modifiers(self):
        for m in self.modifiers:
            if m.shouldRun(obj_graph=self.obj_graph):
                m.apply(obj_graph=self.obj_graph) 
    
    def _apply_instance_modifiers(self):
        pass

    def _finalize_objects_structure(self):
        #import model_graph
        #self.class_graph = model_graph.m_graph.ou
        for node, node_data in self.obj_graph.nodes(data=True):
            for _, to_node, link_data in self.obj_graph.out_edges([node], data=True):
                if link_data["rel_type"] == Many:
                    if not isinstance(getattr(node_data["instance"], link_data["local_attr"]), list):
                        setattr(node_data["instance"], link_data["local_attr"], [])
                    getattr(node_data["instance"], link_data["local_attr"]).append(self.obj_graph.node[to_node]["instance"])
                elif link_data["rel_type"] == One:
                    setattr(node_data["instance"], link_data["local_attr"], self.obj_graph.node[to_node]["instance"])

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


class ABuilder:
    """
        Main interface class for the ``builders`` package.

        For example::

          class Bar:
              bar = 1


          class Foo:
              baz = 10
              bars = Collection(Bar)


          my_foo = Builder(Foo).withA(NumberOf(Foo.bars, 5)).build()
    """
    def __init__(self, clazzToBuild):
        '''
            :arg clazzToBuild: a model class with :py:class:`builders:construct:Construct` fields to populate

            Creates new :py:class:`builders.builder.Builder` instance. Instance contains it's own set of modifiers (see :py:method:`withA`) and produces one result tree at a time.
        '''

        self.clazz = clazzToBuild
        self.modifiers = []
        logger.debug("New builder for clazz <%s>" % self.clazz)

    def _buildclazz(self, clazzToBuild):
        [m.apply(clazz=self.clazz) for m in self.modifiers if m.shouldRun(clazz=self.clazz)]

        instance = self.clazz()
        logger.debug('Created new instance %s of clazz %s' % (instance, self.clazz))

        def make_construct(name, construct):
            logger.debug('Constructing <%s.%s>' % (self.clazz, name))
            setattr(instance, name, construct.build(self.modifiers, instance=instance))

        logger.debug('Creating nested constructst of %s' % instance)
        for name, value in getmembers(instance, lambda x: isinstance(x, construct.Construct) and not isinstance(x, construct.Uplink)):
            make_construct(name, value)

        logger.debug('Creating uplinks of %s' % instance)
        for name, value in getmembers(instance, lambda x: isinstance(x, construct.Uplink)):
            make_construct(name, value)

        # instance level modifier application
        for modifier in self.modifiers:
            if modifier.shouldRun(instance=instance):
                modifier.apply(instance=instance)

        return instance

    def build(self):
        """
            Build the resulting instance with the respect of all of the previously applied modifiers.
        """
        return self._buildclazz(self.clazz)

    def withA(self, *modifiers):
        """
            :arg modifiers: list of modifiers to apply

            Apply a number of modifiers to this builder.
            Each modifier can be either a single :py:class:`builders.modifiers.Modifier` or a nested list structure of them.

            Modifiers are stored in the builder and executed on the ``build`` call.
        """

        modifiers = flatten(modifiers)
        for mod in modifiers:
            try:
                self.modifiers += list(mod)
            except:
                self.modifiers.append(mod)
        return self

