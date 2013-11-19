Basic tutorial
==============

``builders``  is intended to facilitate test data creation and achieves it per two major capabilities:

* :ref:`Describing <model>` data structure via class-like model
* :ref:`Building <build>` of a particular :ref:`finely-configured <modify>` data set


.. _model:

Describing data model
---------------------

Data models are commonly considered as large trees of crossreferenced objects.

For example, to describe a decomposition of a convenient automobile one might draw something like that:

.. digraph:: car

      car [shape=box];
      car -> engine;
      car -> body;
      car -> gearbox;
      car -> wheels [style=dotted];
      wheels -> wheel_A;
      wheels -> wheel_B;
      wheels -> wheel_C;
      wheels -> wheel_D;
      body -> left_seat;
      body -> right_seat;

The diagram declares that car consists of engine, gearbox, body and a set of wheels, completely ommiting the properties of each object.

Same can be described with ``builders`` as follows:

.. code-block:: python

   from builders.construct import Unique, Collection, Random

   class Engine:
       hp = 100
       type = 'steam'

   class Gearbox:
       gears = 4
       type = 'manual'

   class Seat:
       material = 'leather'

   class Body:
       color = 'blue'
       left_seat = Unique(Seat)
       right_seat = Unique(Seat)

   class Wheel:
       size = 14
       threading = 'diagonal'
       type = 'winter_spiked'

   class Car:
       make = 'ford'
       year_of_make = Random(1990, 2005)

       engine = Unique(Engine)
       gearbox = Unique(Gearbox)
       body = Unique(Body)
       wheels = Collection(Wheel, number=4)


The example is mostly self-describing. However, note:

* each data model type has its own python class as a representation
* default attribute values are given in the classes in primitives
* references to other model types are declared via :py:class:`Construct <builders.construct.Construct>` attributes
* there is no explicit **root** element or mandatory base classes


.. _build:

Building model instance
-----------------------

Long story short, building the model is as easy as:

.. code-block:: python

   from builders.builder import Builder

   my_car = Builder(Car).build()

   isinstance(my_car, Car)  # True
   my_car.engine.hp == 100  # True
   len(my_car.wheels)  # 4
   type(my_car.wheels)  # list
   my_car.wheels[0] == my_car.wheels[1]  # False, these are different wheels
   1990 <= my_car.year_of_make <= 2005  # True, exact value of year_of_make varies


How this works? ``Builder`` recursevily walks over the tree starting with ``Car`` and instantiates model classes.

When a class instance is created, each attribute that is a :py:class:`Construct <builders.construct.Construct>` has its ``build`` method called.
The resulting value is then assigned to that attribute of a built instance.

The :py:class:`Unique <builders.construct.Unique>` builds a single new instance of given type thus performing recursion step. :py:class:`Collection <builders.construct.Collection>` builds a number of new instances and puts them in a list.

There are several other useful constructs:

* :py:class:`builders.construct.Random` generate a random number or string
* :py:class:`builders.construct.Uid` generates a new UUID
* :py:class:`builders.construct.Reused` works like ``Unique``, but caches built values
* :py:class:`builders.construct.Maybe` builds a nested construct in a certain conditions
* :py:class:`builders.construct.Lambda` runs passed function with instance being constructed as parameter every time object is built


All the built-in constructs can be found at :py:mod:`builders.construct`. Custom constructs may be derived from :py:class:`builders.construct.Construct`.


.. _modify:

Modifying a tree
----------------


To build non-default model (and thats what you need most of the time) just apply some :py:class:`Modifiers <builders.modifier.Modifier>` to the tree like this:


.. code-block:: python

   from builders.modifiers import InstanceModifier, NumberOf

   my_car = Builder(Car).withA(NumberOf(Car.wheels, 5)).build()

   len(my_car.wheels)  # 5, we told it to be so

   my_car = Builder(Car).withA(InstanceModifier(Seat).thatSets(material='fabric')).build()

   my_car.body.left_seat.material  # 'fabric'
   my_car.body.right_seat.material  # 'fabric'


The ``withA`` method accepts a number of modifiers and returns same ``Builder`` for the sake of chaining:

.. code-block:: python

   from builders.modifiers import InstanceModifier, NumberOf

   Builder(Car).withA(NumberOf(Car.wheels, 5)).withA(InstanceModifier(Engine).thatSets(hp='over_9000')).withA(InstanceModifier(Body).thatSets(color='red')).build()


Obviously, configured ``builder`` can be used again to produce a another one similar car.

Useful built-in modifiers are:

* :py:class:`builders.modifiers.InstanceModifier` factory that makes fancy ``thatDoes``, ``thatSets`` and ``thatSetsCarefully`` modifiers,
* :py:class:`builders.modifiers.NumberOf` that sets ``Collection`` sizes
* :py:class:`builders.modifiers.OneOf` that modifies a ``Collection`` entry
* :py:class:`builders.modifiers.Enabled` that turns on :py:class:`builders.construct.Maybe`

All the built-in modifiers can be found in :py:mod:`builders.modifiers`.