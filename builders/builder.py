import construct
import collections

from inspect import getmembers

from builders.logger import logger


def flatten(l):
    """
        :arg l: iterable to flatten

        Generator that flattens iterable infinitely. If an item is iterable, ``flatten`` descends on it.
        If it is callable, it descends on the call result (with no arguments), and it yields the item itself otherwise.
    """
    if isinstance(l, collections.Iterable) and not isinstance(l, basestring):
        for el in l:
            for sub in flatten(el):
                yield sub
    elif callable(l):
        for sub in flatten(l()):
            yield sub
    else:
        yield l


class Builder:
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
