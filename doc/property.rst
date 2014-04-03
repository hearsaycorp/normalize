
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

.. autofunction:: normalize.property.make_property_type

.. automodule:: normalize.property.types
   :undoc-members:

.. _coll:

Properties containing collections
---------------------------------

.. automodule:: normalize.property.coll
   :undoc-members:

.. _json:

Declaring JSON hints on Properties
----------------------------------

.. automodule:: normalize.property.json

.. _meta:

Addendum: Property MetaClass
----------------------------

.. automodule:: normalize.property.meta
   :undoc-members:

