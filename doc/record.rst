
Defining Records - ``normalize.record``
=======================================

.. automodule:: normalize.record
   :special-members: __init__, __getnewargs__, __getstate__, __setstate__, __str__, __repr__, __eq__, __ne__, __pk__, __hash__

Record Flavors
--------------

``Record`` subclasses don't have any special mix-in magic like
``Property`` subclasses do.  To use a ``Record`` subclass you must
explicitly derive it.  The most useful classes for general use are
:py:class:`normalize.record.json.JsonRecord`,
:py:class:`normalize.record.RecordList` and the combination,
:py:class:`normalize.record.json.JsonRecordList`.

Collection Types
^^^^^^^^^^^^^^^^

Collections are types of records, with a single property ``values``
which contains the underlying collection object.

.. automodule:: normalize.coll
   :members:
   :special-members: __init__, __getnewargs__, __getstate__, __setstate__, __str__, __repr__, __eq__, __ne__, __pk__, __hash__, __reduce__

``JsonRecord``
^^^^^^^^^^^^^^

.. automodule:: normalize.record.json
   :members:
   :special-members: __init__

Customizing JsonRecord Marshalling
""""""""""""""""""""""""""""""""""

JSON record marshalling can be overridden in two important ways:

1. By specifying ``json_in`` (or just ``coerce`` if you want to be
   able to pass in values like this from Python as well) and
   ``json_out`` on your ``Properties``, and the ``json_name`` key.

   Remember, you don't need to explicitly instantiate ``JsonProperty``
   objects; you can throw on these JSON specialization flags on any
   property and :py:mod:`normalize.property.meta` will mix them in for
   you.

   See :ref:`json` for more details.

2. Via the sub-class API.  The most convenient hooks are
   :py:meth:`JsonRecord.json_to_initkwargs` (you must derive
   ``JsonRecord`` for this) and :py:meth:`JsonRecord.json_data` (any
   class can define this).  This is a more general API which can perform
   more 'drastic' conversions, for instance if you want to marshall your
   class to a JSON Array.


Record MetaClass
----------------

.. automodule:: normalize.record.meta
   :members:
   :undoc-members:
   :special-members: __new__
