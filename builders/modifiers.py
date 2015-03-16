from builders.logger import logger
import construct
import model_graph as graph_utils


__all__ = ['Modifier', 'InstanceModifier', 'ValuesMixin', 'ClazzModifier', 'ConstructModifier', 'Given', 'NumberOf', 'HavingIn', 'OneOf', 'Enabled', 'Disabled', 'LambdaModifier', 'Another']


class Modifier(object):
    """
    Base class for build process modifiers.
    Child classes should implement ``apply`` method.
    """
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

    def shouldRun(self, obj_graph=None, **kwargs):
        return obj_graph

    def do(self, obj_graph):
        raise NotImplementedError("Do not use ModelStructureModifier on it's own")

    def apply(self, obj_graph=None, modifiers=(), **kwargs):
        if obj_graph:
            return self.do(obj_graph, modifiers=[m for m in modifiers if m != self], **kwargs)



class HavingIn(ModelStructureModifier):
    """
    Adds ``instances`` to a given :py:class:`builders.constructs.Collection`.

    If ``instance`` is a number, **that much** new instances are added to the ``Collection`` target number.

    Else, that ``instance`` is added to the ``Collection`` as a pre-built one.
    """
    def __init__(self, what, *instances):
        assert isinstance(what, construct.Collection)

        self.what = what
        self.value = instances
        self.obj_graph = None
        
        from model_graph import m_graph
        self.container_class = graph_utils.get_out_edges_by_(m_graph, link_attr="construct", value=self.what)[0][0]

    def _add_successor_object(self, container=None, what=None, modifiers=()):
        assert container is not None
        new_child, child_graph = (None, None)
        
        if what is None:
            from builder import Builder
            new_child, child_graph = Builder(self.what.type).withA(modifiers).build(with_graph=True, do_finalize=False)
            child_graph.remove_nodes_from(child_graph.successors(self.container_class))
            self.obj_graph.add_nodes_from(child_graph.nodes(data=True))
            self.obj_graph.add_edges_from(child_graph.edges(data=True))
        else:
            assert isinstance(what, self.what.type)
            new_child = what
            #child_graph = what.__object_graph__

        graph_utils.link_instance_nodes(self.obj_graph, container, new_child)
        

    def do(self, obj_graph, modifiers=()):
        self.obj_graph = obj_graph
        for instance in obj_graph.successors(self.container_class):
            for something_new in self.value:
                if isinstance(something_new, (int, long)):
                    for _ in xrange(something_new):
                        self._add_successor_object(container=instance, modifiers=modifiers)
                elif isinstance(something_new, self.what.type):
                    self._add_successor_object(container=instance, what=something_new)
                else:
                    raise Exception("You must provide a NUMBER or an INSTANCE of %s for this HavingIn modifier" % self.what.type.__name__)


class NumberOf(HavingIn):
    """
    Sets the target number of :py:class:`builders.constructs.Collection` elements to a given ``amount``
    """
    def __init__(self, what, amount):
        HavingIn.__init__(self, what, amount)
        self.value = amount

    def do(self, obj_graph, modifiers=()):
        self.obj_graph = obj_graph
        for instance in obj_graph.successors(self.container_class):
            child_links = graph_utils.get_out_edges_by_(obj_graph, instance, link_attr="construct", value=self.what)
            assert self.value >= len(child_links), "NumberOf %s elements (%d) can't be smaller than already exist (%d)" % (self.what.type.__name__, self.value, len(child_links))
            for _ in xrange(self.value - len(child_links)):
                self._add_successor_object(container=instance, modifiers=modifiers)


class Given(object):
    """
    Supplied pre-defined ``value`` for a given ``construct``.
    """
    def __init__(self, what, something):
        self.what = what
        self.value = something
        
        from model_graph import m_graph
        self.edge = graph_utils.get_out_edges_by_(m_graph, link_attr="construct", value=self.what)[0]
        self.container_class = self.edge[0]

    def shouldRun(self, instance=None,  obj_graph=None, **kwargs):
        from model_graph import BuilderModelClass
        if isinstance(self.value, BuilderModelClass):
            return obj_graph
        else:
            return isinstance(instance, self.container_class)

    def apply(self, obj_graph=None, instance=None, **kwargs):
        if obj_graph or instance:
            return self.do(obj_graph, instance)

    def do(self, obj_graph, instance):
        #TODO: need support for given collections
        from model_graph import BuilderModelClass, get_out_edges_by_, get_in_edges_by_
        if instance is not None:
            setattr(instance, self.edge[-1]["local_attr"], self.value)
        elif obj_graph is not None:
            for instance in obj_graph.successors(self.container_class):
                if isinstance(self.value, BuilderModelClass):
                    out_edges = get_out_edges_by_(obj_graph, node=instance, link_attr="local_attr", value=self.edge[-1]["local_attr"])
                    in_edges = get_in_edges_by_(obj_graph, node=instance, link_attr="remote_attr", value=self.edge[-1]["local_attr"])
                    obj_graph.remove_edges_from(out_edges + in_edges)
                    graph_utils.remove_node_unconnected_components(obj_graph, instance)
                    graph_utils.link_instance_nodes(obj_graph, instance, self.value)
                


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


class ConstructModifier(ClazzModifier):
    """
    Base class for :py:class:`ClazzModifier` that work on a particular ``construct`` object within a class

    Siblings should implement ``doApply`` method.
    """

    def __init__(self, construct):
        self.construct = construct

    def do(self, clazz):
        logger.debug('%s applied to %s' % (self, clazz))
        for name, value in classvars(clazz).items():
            logger.debug('Checking %s attr <%s> of value %s' %
                         (clazz, name, value))
            if value == self.construct:
                logger.debug('Applying %s to the clazz %s attr <%s> with value %s' % (self, clazz, name, self.value))
                self.doApply(value)


'''
class Given(ConstructModifier):
    """
    Supplied pre-defined ``value`` for a given ``construct``.
    """
    def __init__(self, construct, value):
        ConstructModifier.__init__(self, construct)
        self.value = value

    def doApply(self, construct):
        construct.value = self.value


class NumberOf(ConstructModifier):
    """
    Sets the target number of :py:class:`builders.constructs.Collection` elements to a given ``amount``
    """
    def __init__(self, what, amount):
        assert isinstance(what, construct.Collection)
        assert isinstance(amount, (int, long))

        ConstructModifier.__init__(self, what)
        self.value = amount

    def doApply(self, construct):
        construct.set(self.value)


class HavingIn(ConstructModifier):
    """
    Adds ``instances`` to a given :py:class:`builders.constructs.Collection`.

    If ``instance`` is a number, **that much** new instances are added to the ``Collection`` target number.

    Else, that ``instance`` is added to the ``Collection`` as a pre-built one.
    """
    def __init__(self, what, *instances):
        assert isinstance(what, construct.Collection)

        ConstructModifier.__init__(self, what)
        self.value = instances

    def doApply(self, construct):
        for i in self.value:
            construct.add(i)
'''


class OneOf(ConstructModifier):
    """
    Applies given ``modifiers`` to one of objects build by :py:class:`builders.construct.Collection`.
    """
    def __init__(self, what, *modifiers):
        assert isinstance(what, construct.Collection)

        ConstructModifier.__init__(self, what)
        self.value = list(modifiers)

    def doApply(self, construct):
        construct.modifiers.append(self.value)


class Enabled(ConstructModifier):
    """
    Turns on given :py:class:`builders.construct.Maybe` once.
    """
    def __init__(self, what):
        assert isinstance(what, construct.Maybe)
        ConstructModifier.__init__(self, what)
        self.value = True

    def doApply(self, construct):
        construct.enabled = True


class Disabled(Enabled):
    """
    Like :py:class:`Enabled`, but the other way around.
    """
    def doApply(self, construct):
        construct.enabled = False


class LambdaModifier(ConstructModifier):
    """
    Replaces function in :py:class:`builders.construct.Lambda` with given new_lambda
    """
    def __init__(self, construct, new_lambda):
        ConstructModifier.__init__(self, construct)
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


def Another(collection, *modifiers):
    """
    Add another instance to given ``collection`` with given ``mod``
    """
    return [HavingIn(collection, 1), OneOf(collection, *modifiers)]


class Group(ConstructModifier):
    """
    Adds ``instances`` to a given :py:class:`builders.constructs.Collection`.

    If ``instance`` is a number, **that much** new instances are added to the ``Collection`` target number.

    Else, that ``instance`` is added to the ``Collection`` as a pre-built one.
    """
    def __init__(self, what, size, *group_rules):
        assert isinstance(what, construct.Collection)

        ConstructModifier.__init__(self, what)
        self.value = [size, group_rules]

    def doApply(self, construct):
        construct.add_group(self.value)


class GroupRule(object):
    def getNextModifier(self, instance):
        raise NotImplementedError("Do not use GroupRule on it's own")

    def hasNextModifier(self, instance=None):
        raise NotImplementedError("Do not use GroupRule on it's own")
    
    def handleGroupElement(self, instance):
        pass


class Same(GroupRule):

    def __init__(self, clazz, field):
        self.clazz = clazz
        self.field = field
        self.saved_instance = None

    def getNextModifier(self, instance=None):
#        mods = []

        if self.saved_instance is None:
            if instance is None:
                return []
            self.saved_instance = instance

        field_value = getattr(self.saved_instance, self.field)
        mods = [InstanceModifier(self.clazz).thatSets(**{self.field : field_value})]
        
#        field_value = getattr(self.saved_instance, self.field)
#        class_field_value = getattr(self.saved_instance.__class__, self.field)
#        if isinstance(class_field_value, construct_package.Construct):
#            if isinstance(class_field_value, construct_package.Collection):
#                mods.append(HavingIn(class_field_value, instance))
#            else:
#                mods.append(Given(class_field_value, instance))
#        else:
#            mods.append(InstanceModifier(self.clazz).thatSets(**{self.field : field_value}))

        return mods

    def handleGroupElement(self, instance):
        assert instance is not None, "You don't have to handle 'None' element"
        if self.saved_instance is None:
            return
        class_field_value = getattr(self.saved_instance.__class__, self.field)
        if isinstance(class_field_value, construct.Uplink) and isinstance(class_field_value.destination, construct.Collection):
            for field, value in class_field_value.clazz.__dict__.items():
                if value == class_field_value.destination:
                    getattr(getattr(self.saved_instance, self.field), field).append(instance)

    def hasNextModifier(self, instance=None):
        return self.saved_instance is not None or instance is not None