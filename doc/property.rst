
``normalize.property`` reference
================================

.. WARNING::

   The ``Property()`` constructor usually returns a different object
   type than the class name passed.  It decides on the keyword
   arguments passed to it which subclass takes those arguments and
   calls that class' constructor instead.

   Hopefully, this implementation detail should not be of huge
   importance to most users.  For more details on how a property class
   is selected, see :ref:`meta`.

Core Property Types
-------------------

.. automodule:: normalize.property
   :no-members:

``Property``
^^^^^^^^^^^^

.. autoclass:: normalize.property.Property
   :members:
   :special-members: __get__, __init__

``LazyProperty``
^^^^^^^^^^^^^^^^

.. autoclass:: normalize.property.LazyProperty
   :members:
   :special-members:

``ROProperty``
^^^^^^^^^^^^^^

.. autoclass:: normalize.property.ROProperty
   :special-members: __get__, __init__

``SafeProperty``
^^^^^^^^^^^^^^^^

.. autoclass:: normalize.property.SafeProperty
   :members:
   :special-members:

"Slow" Property types: ``LazySafeProperty``, ``ROLazyProperty``, ``SlowLazyProperty``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Your lazy attributes will normally end up with these types.  All it
means is that the ``__get__`` descriptor is always called, even after
the default has been assigned, because the ``__set__`` descriptor must
also exist to unforce the type safety or keep the property read-only.
If you add ``unsafe`` to the ``traits`` parameter, then you can avoid
this (very minor) slowdown.

.. autoclass:: normalize.property.SlowLazyProperty
   :show-inheritance:

.. autoclass:: normalize.property.LazySafeProperty
   :show-inheritance:

.. autoclass:: normalize.property.ROLazyProperty
   :show-inheritance:

.. _types:

Typed Properties
----------------

Typed properties are convenient shorthands to specifying the various
``isa`` and ``coerce`` parameters when declaring properties.

Bundled Typed Properties
^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: normalize.property.types
   :undoc-members:

Rolling your own typed properties
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: normalize.property.make_property_type

.. _coll:

Properties containing collections
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following typed properties are similar to the other typed
properties, in that they provide some checks and convenience around
making new collection types and hooking them up correctly.

.. autoclass:: normalize.property.coll.CollectionProperty
   :members:
   :show-inheritance:
   :special-members: __get__, __init__

.. autoclass:: normalize.property.coll.SafeCollectionProperty
   :show-inheritance:
   :special-members: __set__

.. autoclass:: normalize.property.coll.ListProperty
   :show-inheritance:
   :special-members: __init__

.. autoclass:: normalize.property.coll.SafeListProperty
   :show-inheritance:

.. _json:

Declaring JSON hints on Properties
----------------------------------

The various ``json_``\ *X* parameters are *distinguishing options*
which will select the "``json``" trait.

.. autoclass:: normalize.property.json.JsonProperty
   :members: json_name, to_json, from_json
   :special-members: __init__, __trait__

The other classes in this module are just mixed-in combinations of
``JsonProperty`` with various other base types.  This is required
because currently the metaclass does not mix them in dynamically.
Once it does, the trivial, undocumented mixes here may be deprecated
or removed.

.. autoclass:: normalize.property.json.SafeJsonProperty
   :show-inheritance:

.. autoclass:: normalize.property.json.LazyJsonProperty
   :show-inheritance:

.. autoclass:: normalize.property.json.LazySafeJsonProperty
   :show-inheritance:

.. autoclass:: normalize.property.json.JsonListProperty
   :show-inheritance:

.. autoclass:: normalize.property.json.SafeJsonListProperty
   :show-inheritance:

There are also two deprecated aliases: ``JsonCollectionProperty`` is
the same as ``JsonListProperty``, and ``SafeJsonCollectionProperty``
is the same as ``SafeJsonListProperty``.

.. _meta:

Addendum: Property MetaClass
----------------------------

This module was mostly a proof of concept.

.. automodule:: normalize.property.meta
   :undoc-members:
   :special-members: __new__

