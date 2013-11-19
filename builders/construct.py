import builder

import modifiers as modifiers_package
import itertools
import random
import uuid


from builders.logger import logger


__all__ = ['Construct', 'Predefined', 'Unique', 'Collection', 'Reused', 'Random', 'Maybe', 'Uplink', 'Uid', 'Key']


class Link:
    """
    Connects this :py:class:`Construct` to another. Used mainly with :py:class:`Uplink`.
    """
    destination = None
    value = None

    def onBuild(self, *args, **kwargs):
        """
        Called when this object is built. Notifies ``self.destination`` that it now has a value.
        """
        if self.destination and kwargs.get('instance'):
            logger.debug('Setting value %s for %s' % (kwargs['instance'], self.destination))
            if not self.value:
                self.destination.value = kwargs['instance']

    def setDestination(self, clazz, destination):
        """
        Configures this link destination and backward link.
        """
        self.clazz = clazz
        self.destination = destination
        try:
            if not self.destination.destination:
                self.destination.setDestination(None, self)
        except AttributeError:
            pass


class Construct(Link):
    """
    Base class for build-generated attributes.
    Subclasses should implement `doBuild` method.
    """
    def build(self, *args, **kwargs):
        """
        Called by :py:class:`builders.builder.Builder` on the model construction.
        Returns actual pre-set value (via :py:class:`Link` mechanism) or a newly built one.
        """
        self.onBuild(**kwargs)
        if self.value:
            logger.debug('%s returning pre-built value %s' % (self, self.value))
            result = self.value
            self.value = None
        else:
            result = self.doBuild(*args, **kwargs)
        return result

    def doBuild(self, *args, **kwargs):
        raise NotImplementedError('This is not implemented')


class Predefined(Construct):
    """
    Builds to a predefined ``value``.
    """
    def __init__(self, value):
        self.value = value

    def doBuild(self, *args, **kwargs):
        return self.value


class Unique(Construct):
    """
    Builds a new instance of ``type`` with a separate :py:class:`builders.Builder`
    with respect to currently active modifiers.
    """
    def __init__(self, typeToBuild):
        self.type = typeToBuild

    def doBuild(self, modifiers, **kwargs):
        return builder.Builder(self.type).withA(*modifiers).build()


class Lambda(Construct):
    """
    Function, executed during each build with an instance being constructed passed in as parameter
    """
    def __init__(self, functionToExecute):
        self.function = functionToExecute

    def doBuild(self, modifiers, **kwargs):
        return self.function(kwargs['instance'])


class Collection(Unique):
    """
    Builds a ``list`` of new ``typeToBuild`` objects.
    With no modifiers, list will contain ``number`` entries.
    """
    def __init__(self, typeToBuild, number=1):
        Unique.__init__(self, typeToBuild)
        self.number = number
        self.overrides = []
        self.items = []
        self.destination = []
        self.modifiers = []

    def add(self, something):
        if isinstance(something, (int, long)):
            self.overrides.append(lambda x: x + something)
        else:
            self.items.append(something)

    def set(self, amount):
        self.overrides.append(lambda x: amount)

    def build(self, *args, **kwargs):
        self.onBuild(**kwargs)
        if self.value:
            logger.debug('%s has a set value %s' % (self, self.value))
            # self.add(self.value)
            self.value = None
        result = self.doBuild(*args, **kwargs)
        return result

    def onBuild(self, *args, **kwargs):
        if self.destination and kwargs.get('instance'):
            logger.debug('Receiving value %s for %s' % (kwargs['instance'], self.destination))
            if not self.value:
                for destination in self.destination:
                    destination.value = kwargs['instance']

    def setDestination(self, clazz, destination):
        self.clazz = clazz
        self.destination.append(destination)
        try:
            if not destination.destination:
                destination.setDestination(None, self)
        except AttributeError:
            pass

    def doBuild(self, modifiers, **kwargs):
        total_amount = self.number
        for o in self.overrides:
            total_amount = o(total_amount)
        self.overrides = []

        result = list(self.items)
        self.items = []

        if self.destination:
            logger.debug("Collection %s found destinations %s" % (self, self.destination))
            saved_value = self.destination[0].value
        else:
            saved_value = None
        while len(result) < total_amount:
            logger.debug("Collection %s building item of type %s" % (self, self.type))
            logger.debug("Collection destination is %s, %s" % (self.destination, modifiers_package.classvars(self.destination)))
            if saved_value:
                self.destination[0].value = saved_value
            if not saved_value and self.destination:
                self.destination[0].value = kwargs['instance']
            extra_modifiers = self.modifiers and self.modifiers.pop()
            item = Unique.doBuild(self, modifiers + extra_modifiers)
            result.append(item)

        return result


class Reused(Unique):
    """
    Like :py:class:`Unique`, but with caching.

    Stores all the built instances within a dictionary. If the would-be-new-instance has key equal to some of the objects in cache, cached object is returned.

    Key is a tuple of ``typeToBuild`` and selected attribute values.

    :param local: keep cache in the `Reused` instance. If false, cache is global (eww).
    :param keys: list of attributes that are considered key components along with the `typeToBuild`.

    """
    __reused_instances = {}

    def __init__(self, typeToBuild, local=False, keys=[]):
        Unique.__init__(self, typeToBuild)
        self.key_components = keys

        if local:
            self.instances = {}
        else:
            self.instances = Reused.__reused_instances

    def doBuild(self, modifiers, **kwargs):
        candidate = Unique.doBuild(self, modifiers)

        key = tuple([self.type] + [getattr(candidate, k) for k in self.key_components])

        if not self.instances.get(key):
            self.instances[key] = Unique.doBuild(self, modifiers)
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

    def doBuild(self, *args, **kwargs):
        if self.enabled:
            self.enabled = False

            return self.construct.doBuild(*args, **kwargs)


class Uplink(Construct):
    """
    Becomes a value of another :py:class:`Construct` when it is build.

    Call ``linksTo`` on ``Uplink`` object to set destination.

    Supplying ``reusing_by`` emulates :py:attr:`Reused` behavior with given ``keys``.

    .. warning::
      ``reusing_by`` is not fully operational at the moment, use at your own risk.
      See ``test_uplink.test_reuse`` -- there are commented checks.
    """

    def __init__(self, reusing_by=[]):
        if reusing_by:
            self.reuser = Reused(None, local=True, keys=reusing_by)
        else:
            self.reuser = None

    def doBuild(self, modifiers, instance=None, **kwargs):
        if not self.destination:
            raise ValueError('Link %s has no attachment' % self)

        logger.debug('Up-linking instance for %s with Given %s value of %s' %
                     (self.clazz, self.destination, instance))

        mods = [modifiers]

        if isinstance(self.destination, Collection):
            mods.append(modifiers_package.HavingIn(self.destination, instance))
        else:
            mods.append(modifiers_package.Given(self.destination, instance))

        if self.reuser:
            return self.reuser.doBuild(modifiers, **dict(instance=instance, **kwargs))
        else:
            return builder.Builder(self.clazz).withA(*mods).build()

    def linksTo(self, clazz, destination):
        if self.reuser:
            self.reuser.type = clazz
        self.setDestination(clazz, destination)


class Random(Construct):
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


class Uid(Construct):
    """
    Builds to a string with a fresh :py:func:`uuid.uuid4`
    """
    def doBuild(self, *args, **kwargs):
        return str(uuid.uuid4())


key_storage = {}


class Key(Construct):
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
        if not cls in key_storage.keys():
            key_storage[cls] = []

        value = next(itertools.dropwhile(lambda x: x in key_storage[cls], self.value_generator(*args, **kwargs)))
        key_storage[cls].append(value)
        return value
