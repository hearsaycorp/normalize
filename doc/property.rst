
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

``SafeProperty``
^^^^^^^^^^^^^^^^

.. autoclass:: normalize.property.SafeProperty
   :members:
   :special-members: __get__
   :show-inheritance:

``LazyProperty``
^^^^^^^^^^^^^^^^

``LazyProperty`` has a function which returns the value for a slot, if
the slot is empty.

.. autoclass:: normalize.property.LazyProperty
   :members:
   :special-members:

.. autoclass:: normalize.property.LazySafeProperty
   :members:
   :show-inheritance:
   :special-members: __get__


``ROProperty`` & ``ROLazyProperty``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

These types cannot be assigned; however ``ROLazyProperty`` may take a
function which provides the initial value on first access; this
function is called at most once for each instance.

.. autoclass:: normalize.property.ROProperty
   :members:
   :special-members: __init__

.. autoclass:: normalize.property.ROLazyProperty
   :members:
   :show-inheritance:
   :special-members: __get__

.. _types:

Typed Properties
----------------

Typed properties are convenient shorthands to specifying the various
``isa`` and ``coerce`` parameters when declaring properties.

Bundled Typed Properties
^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: normalize.property.types
   :members:
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
   :members:
   :show-inheritance:
   :special-members: __set__

.. autoclass:: normalize.property.coll.ListProperty
   :members:
   :show-inheritance:
   :special-members: __init__

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
   :members:
   :show-inheritance:

.. autoclass:: normalize.property.json.JsonListProperty
   :members:
   :show-inheritance:

There are also two deprecated aliases: ``JsonCollectionProperty`` is
the same as ``JsonListProperty``.

.. _meta:

Addendum: Property MetaClass
----------------------------

.. automodule:: normalize.property.meta
   :members:
   :undoc-members:
   :special-members: __new__

