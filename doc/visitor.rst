``normalize.visitor`` reference
===============================
This Visitor class is an early attempt at abstracting the various
visitor functions used through the rest of the module.

It is not currently complete; notably, it should be possible to use
this class without an instance, such as to implement marshal in.
There is also the gaping lack of support for avoiding infinite
recursion in the event of data structures with cycles, just like the
rest of this module.

.. TIP::
   Don't pass data structures with cycles into any normalize
   visitor function.  You have been warned.

.. autoclass:: normalize.visitor.Visitor
   :members: __init__, is_filtered, field_selector, push, pop, copy

.. autoclass:: normalize.visitor.VisitorPattern
   :members: visit, cast, reflect, unpack, apply, aggregate, reduce, grok, reverse, collect, produce, scantypes, propinfo, typeinfo, itemtypes, StopVisiting, map, map_record, map_prop, map_collection, map_type_union
