
Defining Records - ``normalize.record``
=======================================

Record Flavors
--------------

``Record`` subclasses don't have any special mix-in magic like
``Property`` subclasses do.  To use a ``Record`` subclass you must
explicitly derive it.  The most useful classes for general use are
:py:class:`normalize.record.json.JsonRecord`,
:py:class:`normalize.record.RecordList` and the combination,
:py:class:`normalize.record.json.JsonRecordList`.

Here's a guide to choosing a class:

``JsonRecord``

    This is a good choice for codebases where you typically want to
    pass the JSON (string or data) as the first positional argument to
    a constructor.  There is one JSON mapping which is the default,
    and it is accessed by ``.json_data()`` (or the constructor).  It
    also has an ``unknown_json_keys`` property, which is is marked as
    'extraneous' and contains all of the input keys which were not
    known.

    The specifics of this conversion can be overridden in many ways;
    you can set ``json_name`` on the property name to override the
    default of using the python property name.  You can also provide
    ``json_in`` and ``json_out`` lambda functions to transform the
    values on the way in and out.

    More 'radical' transforms can be achieved by overriding
    ``json_data`` in your class for marshal out, and
    ``json_to_initkwargs`` for marshall in.

``Record``

    This version is a good choice where the sources of data are
    typically other python functions.  The default is a conversion
    from a dict, but the keys are the actual property names, not the
    ``json_name`` versions like ``JsonRecord``.

    It's also good for object types which have multiple JSON mappings,
    where you don't want to make any of them more special than any
    other.  Instead of using the ``.json_data()`` function, you might
    for instance be using :py:class:`normalize.visitor.Visitor`.

    You can still access the same conversion as with ``JsonRecord`` by
    using the :py:func:`normalize.record.json.to_json` and
    :py:func:`normalize.record.json.from_json` functions directly.
    These functions will respect any :py:class:`JsonProperty` hints
    (``json_name`` etc), even if those hints are on properties which
    are not a part of a ``JsonRecord`` class.

``RecordList``

    The ``RecordList`` type is a specialization of ``Record``, which
    expects its first constructor argument to be a list.  Internally
    this is just a ``Record`` which has a ``values`` property, and
    this property is the actual collection.  This ``values`` property
    isn't currently present in the ``type(Foo).properties``
    dictionary, but may some day show up there.

    In theory, ``RecordList`` is just one of possibly many types of
    :py:class:`normalize.coll.Collection` sets which happens to use
    continuous integers as the key.  Each collection type provides
    methods which know how to interpret iterable things and convert
    them into an iterable of (K, V) pairs.  In practice, the list is
    the only type which is currently reasonably implemented or tested.

    This base class implements the various methods expected of
    collections (iterators, getitem, etc).  It mostly just passes
    these down to the underlying ``values``, but you can expect this
    behavior to get more typesafe as time goes on (so that you can't,
    for instance, add records of the wrong type to a list).

``JsonRecordList``

    This is really just a ``RecordList`` sub-type which uses
    ``json_to_initkwargs`` to handle the conversion from and from a
    list.  So by default, the constructor expects a list, and the
    ``json_data`` method returns one, too.  You can also use this type
    for when you're dealing with Json data which is logically a list,
    but actually is a dict, with some top-level keys, and one of the
    keys with the list in it as well, by customizing the
    ``json_to_initkwargs`` method.  eg, a "next page" URL key, resume
    token, or a count of the size of the set.

That's a summary overview; apologies if I end up repeating myself over
the rest of this page!

``Record``
^^^^^^^^^^

.. autoclass:: normalize.record.Record
   :members: __init__, __getnewargs__, __getstate__, __setstate__, __str__, __repr__, __eq__, __ne__, __pk__, __hash__


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
