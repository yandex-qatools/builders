import construct
from builders.logger import logger


__all__ = ['Modifier', 'InstanceModifier', 'ValuesMixin', 'ClazzModifier', 'ConstructModifier', 'Given', 'NumberOf', 'HavingIn', 'OneOf', 'Enabled', 'LambdaModifier', 'Another']


class Modifier:
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
    Turns on given :py:class:`builders.construct.Maybe`
    """
    def __init__(self, what):
        assert isinstance(what, construct.Maybe)
        ConstructModifier.__init__(self, what)
        self.value = True

    def doApply(self, construct):
        construct.enabled = True


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


class ValuesMixin:
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
