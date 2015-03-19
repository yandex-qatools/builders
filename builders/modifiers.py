from builders import graph_utils
from builders.logger import logger
import construct
import networkx as nx


__all__ = ['Modifier', 'InstanceModifier', 'ValuesMixin', 'ClazzModifier', 'ConstructModifier', 'Given', 'NumberOf', 'HavingIn', 'OneOf', 'Enabled', 'Disabled', 'LambdaModifier', 'Another']


class Modifier(object):
    """
    Base class for build process modifiers.
    Child classes should implement ``apply`` method.
    """
    
    priority = 9999 # :)
    
    def apply(self, *args, **kwargs):
        """
        Perform the actual modification.
        ``kwargs`` can contain different parameters -- modifier is encouraged to check actual values supplied.
        See :py:class:`builders.builder.Builder` to find out how this is invoked.
        """
        raise NotImplementedError('This is not implemented')

    def shouldRun(self, *args, **kwargs):
        """
        Determines if the modifier should run on this particular occasion

        Parameters are similar to the ``apply`` method
        """

    def __add__(self, other):
        """
        Emulates ordered sum of modifiers -- returns list of addends.
        Example usage::
          my_foobar_modifier = MyFooModifier('green') + MyBarModifier('spam')
        """
        return [self, other]


class ModelStructureModifier(Modifier):
    """
    Base class for :py:class:`Modifier` siblings that act at classes.

    Siblings should implement ``do`` method.

    See :py:class:`builders.builder.Builder` to see the actual invocation.
    """

    def do(self, graph, modifiers=()):
        raise NotImplementedError("Do not use ModelStructureModifier on it's own")

    def apply(self, graph, modifiers=(), **kwargs):
        return self.do(graph, modifiers=[m for m in modifiers if m != self], **kwargs)

    def get_links(self, graph, node=None, uplink=False):
        from builders.model_graph import Link
        search_by = "construct" if not uplink else "uplink_for"
        return [Link(*link, graph=graph) for link in graph_utils.get_out_edges_by_(graph, node=node, link_attr=search_by, value=self.what)]

    def get_default_link(self):
        from builders.model_graph import m_graph
        return self.get_links(m_graph)[0]

    def get_default_uplink(self):
        from builders.model_graph import m_graph
        uplinks = self.get_links(m_graph, uplink=True)
        if uplinks:
            return uplinks[0]
        else:
            return None

    def get_affected_nodes(self, graph):
        links = self.get_links(graph)
        nodes = []
        for link in links:
            if link.source() not in nodes:
                nodes.append(link.source())
        return nodes

    def get_affected_destination_nodes(self, graph):
        links = self.get_links(graph)
        nodes = []
        for link in links:
            if link.destination() not in nodes:
                nodes.append(link.destination())
        return nodes


class DataDependentModifier(ModelStructureModifier):
    def shouldRun(self, object_graph=None, **kwargs):
        return object_graph

    def apply(self, object_graph=None, modifiers=(), **kwargs):
        if object_graph:
            ModelStructureModifier.apply(self, object_graph, modifiers)


class DataIndependentModifier(ModelStructureModifier):
    def shouldRun(self, class_graph=None, **kwargs):
        return class_graph

    def apply(self, class_graph=None, modifiers=(), **kwargs):
        if class_graph:
            ModelStructureModifier.apply(self, class_graph, modifiers)


class NumberOf(DataIndependentModifier):
    """
    Sets the target number of :py:class:`builders.constructs.Collection` elements to a given ``amount``
    """
    priority = 20
    def __init__(self, what, amount):
        assert isinstance(what, construct.Collection)
        self.what = what
        self.value = amount

    def do(self, graph, modifiers=()):
        links = self.get_links(graph)
        if len(links) <= self.value:
            default_link = self.get_default_link()
            [default_link.add_to(graph) for _ in range(self.value - len(links))]
            if len(links) == 0:
                uplink = self.get_default_uplink()
                if uplink:
                    uplink.add_to(graph)
        else:
            [links[-1 - i].remove() for i in range(len(links) - self.value)]
            if self.value == 0:
                uplinks = self.get_links(graph, uplink=True)
                [uplink.remove() for uplink in uplinks]


class More(NumberOf):
    def __init__(self, what, amount):
        assert isinstance(what, construct.Collection)
        self.what = what
        self.value = amount

    def do(self, graph, modifiers=()):
        self.value += len(self.get_links(graph))
        NumberOf.do(self, graph, modifiers)


class Enabled(DataIndependentModifier):
    """
    Turns on given :py:class:`builders.construct.Maybe` once.
    """
    priority = 10
    def __init__(self, what):
        assert isinstance(what, construct.Maybe)
        self.what = what

    def do(self, graph, modifiers=()):
        links = self.get_links(graph)
        if links:
            return
        
        self.get_default_link().add_to(graph)
        uplink = self.get_default_uplink()
        if uplink:
            uplink.add_to(graph) 
        

class Disabled(Enabled):
    """
    Like :py:class:`Enabled`, but the other way around.
    """
    def do(self, graph, modifiers=()):
        [link.remove() for link in self.get_links(graph)]
        [uplink.remove() for uplink in self.get_links(graph, uplink=True)]


class HavingIn(DataDependentModifier):
    def __init__(self, what, *instances):
        assert isinstance(what, construct.Collection)
        for obj in instances:
            assert isinstance(obj, what.getTypeToBuild())
        self.what = what
        self.value = instances

    def do(self, graph, modifiers=()):
        affected_objs = self.get_affected_nodes(graph)
        for obj in affected_objs:
            links = self.get_links(graph, obj)
            attr = links[0].source_attr()
            value = getattr(obj, attr)
            for i in xrange(len(self.value)):
                if value:
                    [link.remove_destination() for link in links if link.destination() == value[-i-1]]
                    value.remove(value[-i-1])
            value += self.value


class Given(DataDependentModifier):
    def __init__(self, what, value):
        assert not isinstance(what, construct.Collection), "Can't apply Given to Collection, use HavingIn instead."
        self.what = what
        self.value = value

    def do(self, graph, modifiers=()):
        links = self.get_links(graph)
        for link in links:
            setattr(link.source(), link.source_attr(), self.value)
            link.remove_destination()


class OneOf(ModelStructureModifier):
    class_graph = None
    class_graph_saved = None

    def __init__(self, what, *modifiers):
        assert isinstance(what, construct.Collection)
        
        self.what = what
        self.value = list(modifiers)
        self.only_first_run = True
        self.executed = False

    def shouldRun(self, instance=None, clazz=None, class_graph=None, object_graph=None, **kwargs):
        return instance or object_graph or clazz or class_graph

    def apply(self, instance=None, clazz=None, class_graph=None, object_graph=None, modifiers=(), **kwargs):
        if self.only_first_run and not self.executed:
            if class_graph:
                self.executed = True
                affected_nodes = self.get_affected_nodes(class_graph)
                
                for node in affected_nodes:
                    links = self.get_links(class_graph, node)
                    
                    new_mod = OneOf(self.what, *self.value)
                    new_mod.only_first_run = False
                    
                    for link in links:
                        if not link.get_extra_mods():
                            link.add_extra_mods(new_mod)
                            break

        elif not self.only_first_run:
            if class_graph:
                self.class_graph = class_graph
                self.class_graph_saved = graph_utils.nondeepcopy_graph(self.class_graph)
            elif object_graph:
                graph_utils.replace_graph(self.class_graph_saved, self.class_graph)

            self.do(instance=instance, clazz=clazz, class_graph=class_graph, object_graph=object_graph)
 

    def do(self, instance, clazz, class_graph, object_graph, modifiers=()):
        for mod in self.value:
            if mod.shouldRun(instance=instance, clazz=clazz, class_graph=class_graph, object_graph=object_graph):
                mod.apply(instance=instance, clazz=clazz, class_graph=class_graph, object_graph=object_graph)


def Another(collection, *modifiers):
    """
    Add another instance to given ``collection`` with given ``mod``
    """
    return [More(collection, 1), OneOf(collection, *modifiers)]


class _ParticularClassModifier(Modifier):
    def __init__(self, classToRunOn, action):
        self.classToRunOn = classToRunOn
        self.action = action

    def shouldRun(self, instance=None, **kwargs):
        return isinstance(instance, self.classToRunOn)

    def apply(self, instance=None, **kwargs):
        if instance:
            return self.action(instance)


class _setter:
    def __init__(self, kwargs, careful=False):
        self.kwargs = kwargs
        self.careful = careful

    def __call__(self, instance):
        for (k, v) in self.kwargs.items():
            if self.careful:
                assert hasattr(instance, k), '<%s> is missing attribute <%s>' % (instance, k)
            setattr(instance, k, v)


class InstanceModifier:
    """
    Modifier factory that builds new modifiers to act upon instances of ``classToRunOn``.

    ``InstanceModifier(foo).thatDoes(bar)`` returns modifier that calls ``bar(x)`` on the ``foo`` istances ``x``

    ``InstanceModifier(foo).thatSets(a=1, b=2)`` returns modifier that sets ``foo`` instance attributes ``a`` to ``1`` and ``b`` to ``2``

    ``InstanceModifier(foo).thatCarefullySets(c=2)`` returns modifier that sets ``foo`` instance attributes ``c`` to ``2`` if that instance already has ``c`` attribute and raises exception if it does not
    """
    def __init__(self, classToRunOn):
        self.classToRunOn = classToRunOn

    def thatDoes(self, action):
        """
        factory method that builds an instance backed by a given callable ``action``
        """
        return _ParticularClassModifier(self.classToRunOn, action)

    def thatSets(self, **kwargs):
        """
        factory method that builds a modifier that sets given kwargs as attributes for the instance
        """
        return self.thatDoes(_setter(kwargs))

    def thatCarefullySets(self, **kwargs):
        """
        as `thatSets` factory method, but asserts that attribute exists
        """
        return self.thatDoes(_setter(kwargs, careful=True))


def classvars(clazz):
    'like vars(clazz) but backed by dir(clazz)'
    return dict([(a, getattr(clazz, a)) for a in dir(clazz)])


class ClazzModifier(Modifier):
    """
    Base class for :py:class:`Modifier` siblings that act at classes.

    Siblings should implement ``do`` method.

    See :py:class:`builders.builder.Builder` to see the actual invocation.
    """

    def shouldRun(self, clazz=None, **kwargs):
        return clazz

    def do(self, clazz):
        raise NotImplementedError("Do not use ClazzModifier on it's own")

    def apply(self, clazz=None, **kwargs):
        if clazz:
            return self.do(clazz)


class ValueConstructModifier(ClazzModifier):
    def __init__(self, constr):
        assert isinstance(constr, construct.ValueConstruct)
        self.construct = constr

    def do(self, clazz):
        logger.debug('%s applied to %s' % (self, clazz))
        for name, value in classvars(clazz).items():
            logger.debug('Checking %s attr <%s> of value %s' %
                         (clazz, name, value))
            if value == self.construct:
                logger.debug('Applying %s to the clazz %s attr <%s> with value %s' % (self, clazz, name, self.value))
                self.doApply(value)


class LambdaModifier(ValueConstructModifier):
    """
    Replaces function in :py:class:`builders.construct.Lambda` with given new_lambda
    """
    def __init__(self, construct, new_lambda):
        ValueConstructModifier.__init__(self, construct)
        self.value = new_lambda

    def doApply(self, lambda_construct):
        if isinstance(lambda_construct, construct.Lambda):
            lambda_construct.alternative_function = self.value
        else:
            raise TypeError("This modifier is applicable only for Lambda construct and it's children, but instead got %s" % type(lambda_construct))


class ValuesMixin(object):
    """
        Syntactic sugar for ``InstanceModifier.thatCarefullySets``. Use it like::

          class Foo(ValuesMixin):
            bar = 0

          class Baz:
            foo = Unique(Foo)

          baz = Builder(Baz).withA(Foo.values(bar=2)).build()
    """

    @classmethod
    def values(clz, **kw):
        return InstanceModifier(clz).thatCarefullySets(**kw)