Frequently Asked Questions
==========================

This is a list of Frequently Asked Questions about builders.  Feel free to suggest new entries!


How do I...
-----------

... set backrefs?
   Use :py:class:`builders.construct.Uplink`.

... simplify ``InstanceModifier``?
   Use :py:class:`builders.modifiers.ValuesMixin`.

... inherit model classes from other model classes?
   At your own risk.

... make sure my random ID's dont collide?
   Use :py:class:`builders.construct.Key` around your ``Random``

... reuse the modifiers?
   They can be placed in a list and fed to the builder like this:

   .. code-block:: python

      big_engine = InstanceModifier(Engine).thatSets(hp=1500)
      big_wheels = InstanceModifier(Wheel).thatSets(size=25)

      monster_car = [big_engine, big_wheels, InstanceModifier(Body).thatSets(color='red')]

      my_monster = Builder(Car).withA(monster_car).build()  # indeed it is


... build something with a circular dependency?
   Add a proper ``InstanceModifier().thatDoes()`` to set non-tree-like references.