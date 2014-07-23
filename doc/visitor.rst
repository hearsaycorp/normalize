``normalize.visitor`` reference
===============================
This Visitor class is an attempt at unifying the various visitor
functions used through the rest of the module, as well as providing a
convenient API for working with normalize data structures.

.. WARNING::
   Cycle detection is still TODO (but close).  Be careful if using
   data structures with cycles.

.. autoclass:: normalize.visitor.Visitor
   :members: __init__, is_filtered, field_selector, push, pop, copy

.. autoclass:: normalize.visitor.VisitorPattern
   :members: visit, cast, reflect, unpack, apply, aggregate, reduce, grok, reverse, collect, produce, scantypes, propinfo, typeinfo, itemtypes, StopVisiting, map, map_record, map_prop, map_collection, map_type_union
