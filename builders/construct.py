from builders import graph_utils
from builders.logger import logger
import itertools
import builder
import random
import uuid




__all__ = ['Construct', 'Predefined', 'Unique', 'Collection', 'Reused', 'Random', 'Maybe', 'Uplink', 'Uid', 'Key', 'Lambda']


class Construct(object):
    """
    Base class for build-generated attributes.
    Subclasses should implement `doBuild` method.
    """
    
    value = None
    clazz = None
    
    def build(self, *args, **kwargs):
        """
        Called by :py:class:`builders.builder.Builder` on the model construction.
        Returns actual pre-set value (via :py:class:`Link` mechanism) or a newly built one.
        """

        if self.value:
            logger.debug('%s returning pre-built value %s' % (self, self.value))
            result = self.value
            self.value = None
        else:
            result = self.doBuild(*args, **kwargs)
        return result

    def doBuild(self, *args, **kwargs):
        raise NotImplementedError('This is not implemented')

    def getValue(self):
        return self.value

    def getDefaultModifiers(self):
        return []


class Unique(Construct):
    """
    Builds a new instance of ``type`` with a separate :py:class:`builders.Builder`
    with respect to currently active modifiers.
    """
    def __init__(self, typeToBuild, uplink=None):
        self.type = typeToBuild
        self.uplink = uplink
        if self.uplink:
            self.uplink.setDestination(self)

    def doBuild(self, modifiers, cl_gr, obj_gr, **kwargs):
        return builder.Builder(self.type).withA(*modifiers)._build(cl_gr, obj_gr)

    def getTypeToBuild(self):
        return self.type


class Collection(Unique):
    """
    Builds a ``list`` of new ``typeToBuild`` objects.
    With no modifiers, list will contain ``number`` entries.
    """
    def __init__(self, typeToBuild, number=1, uplink=None):
        Unique.__init__(self, typeToBuild, uplink)
        self.number = number

    def doBuild(self, modifiers, cl_gr, obj_gr, **kwargs):
        return builder.Builder(self.type).withA(*modifiers)._build(cl_gr, obj_gr)

    def getDefaultModifiers(self):
        from modifiers import NumberOf
        return [NumberOf(self, self.number)]


class Reused(Unique):
    """
    Like :py:class:`Unique`, but with caching.

    Stores all the built instances within a dictionary. If the would-be-new-instance has key equal to some of the objects in cache, cached object is returned.

    Key is a tuple of ``typeToBuild`` and selected attribute values.

    :param local: keep cache in the `Reused` instance. If false, cache is global (eww).
    :param keys: list of attributes that are considered key components along with the `typeToBuild`.

    """
    __reused_instances = {}

    def __init__(self, typeToBuild, local=False, keys=[], uplink=None):
        Unique.__init__(self, typeToBuild, uplink)
        self.key_components = keys

        if local:
            self.instances = {}
        else:
            self.instances = Reused.__reused_instances

    def doBuild(self, modifiers, cl_gr, obj_gr, **kwargs):
        candidate = Unique.doBuild(self, modifiers, graph_utils.nondeepcopy_graph(cl_gr), graph_utils.nondeepcopy_graph(obj_gr)) #Careful here!!! think about modifiers

#        for node in obj_gr.nodes():
#            if [node for k in self.key_components if getattr(candidate, k) == getattr(node, k)]:
#                return node
#
#        return Unique.doBuild(self, modifiers, cl_gr, obj_gr)

        key = tuple([self.type] + [getattr(candidate, k) for k in self.key_components])

        if not self.instances.get(key):
            self.instances[key] = Unique.doBuild(self, modifiers, cl_gr, obj_gr)
        return self.instances[key]


class Maybe(Construct):
    """
    Returns result of nested ``construct`` if ``enabled``.

    See :py:class:`builders.modifiers.Enabled` to turn it on.
    """

    def __init__(self, construct, enabled=False):
        assert isinstance(construct, Unique)

        self.construct = construct
        self.enabled = enabled
        self.type = construct.type
        self.uplink = construct.uplink
        if self.uplink:
            self.uplink.setDestination(self)

    def build(self, *args, **kwargs):
        return self.construct.doBuild(*args, **kwargs)

    def getTypeToBuild(self):
        return self.construct.type

    def getValue(self):
        return self.construct.getValue()

    def getDefaultModifiers(self):
        from modifiers import Disabled
        return [Disabled(self)] if not self.enabled else []


class Uplink(Unique):
    """
    Becomes a value of another :py:class:`Construct` when it is build.

    Call ``linksTo`` on ``Uplink`` object to set destination.

    Supplying ``reusing_by`` emulates :py:attr:`Reused` behavior with given ``keys``.

    .. warning::
      ``reusing_by`` is not fully operational at the moment, use at your own risk.
      See ``test_uplink.test_reuse`` -- there are commented checks.
    """

    def __init__(self):
        Unique.__init__(self, None)
        self.destination_construct = None

    def setDestination(self, remote_construct = None, type_to_build = None):
        if remote_construct:
            self.destination_construct = remote_construct
        if type_to_build:
            self.type = type_to_build

    def getLinkDestination(self):
        return (self.destination_construct, self.type)

    def doBuild(self, modifiers, cl_gr, obj_gr, **kwargs):
        return builder.Builder(self.type).withA(*modifiers)._build(cl_gr, obj_gr)

    #TODO: add linksTo



class ValueConstruct(object):
    value = None
    
    def build(self, *args, **kwargs):
        """
        Called by :py:class:`builders.builder.Builder` on the model construction.
        Returns actual pre-set value (via :py:class:`Link` mechanism) or a newly built one.
        """

        if self.value:
            logger.debug('%s returning pre-built value %s' % (self, self.value))
            result = self.value
            self.value = None
        else:
            result = self.doBuild(*args, **kwargs)
        return result

    def doBuild(self, *args, **kwargs):
        raise NotImplementedError('This is not implemented')


class Predefined(ValueConstruct):
    """
    Builds to a predefined ``value``.
    """
    def __init__(self, value):
        self.value = value

    def doBuild(self, *args, **kwargs):
        return self.value


class Lambda(ValueConstruct):
    """
    Function, executed during each build with an instance being constructed passed in as parameter
    """
    def __init__(self, functionToExecute):
        self.default_function = functionToExecute
        self.alternative_function = None

    def doBuild(self, *args, **kwargs):
        if not self.alternative_function:
            value = self.default_function(kwargs['instance'])
        else:
            value = self.alternative_function(kwargs['instance'])
            self.alternative_function = None
        return value



class Random(ValueConstruct):
    """
    :arg start: random interval start
    :arg end: random interval end
    :arg pattern: a string %-pattern with single non-positional argument

    A construct that results in a random integer or random string.
    If ``pattern`` is present, it is formatted with the random value.
    """
    def __init__(self, start=1, end=100500, pattern=None):
        self.start = start
        self.end = end
        self.pattern = pattern

    def doBuild(self, *args, **kwargs):
        value = random.randint(self.start, self.end)
        if self.pattern:
            return self.pattern % value
        else:
            return value


class Uid(ValueConstruct):
    """
    Builds to a string with a fresh :py:func:`uuid.uuid4`
    """
    def doBuild(self, *args, **kwargs):
        return str(uuid.uuid4())


key_storage = {}


class Key(ValueConstruct):
    """
    Tries to obtain fresh items from ``value_construct`` upon build via checking new item against all the previously built ones.

    :raises Exception: if it fails to get a non-used value after a meaningful number of attempts.

    Intended to be used with :py:class:`Random` to prevent key collisions like::

      class MyFoo:
        id = Key(Random())
    """
    def __init__(self, value_construct):

        def value_generator(*args, **kwargs):
            MAX_ATTEMPTS = 1000
            for _ in xrange(MAX_ATTEMPTS):
                yield value_construct.doBuild(*args, **kwargs)
            raise Exception("Can't get unique key value! Max attempts expended.")
        self.value_generator = value_generator

    def doBuild(self, *args, **kwargs):
        cls = kwargs['instance'].__class__
        if cls not in key_storage.keys():
            key_storage[cls] = []

        value = next(itertools.dropwhile(lambda x: x in key_storage[cls], self.value_generator(*args, **kwargs)))
        key_storage[cls].append(value)
        return value
