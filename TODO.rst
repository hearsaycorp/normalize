TODO
====

* switch sense of 'safe' properties; safe should be the default,
  unsafe only by request.  Detect non-sensible combinations.

* copy constructor (teaching ``__init__()`` to take an object might
  work), to be used by ``MultiFieldSelector([]).get()``

* ``FieldSelector`` should define ``__or__()`` to return a
  ``MultiFieldSelector``

* exceptions:

  * need to be proper classes;

  * should return context information when marshaling in (perhaps
    containing ``FieldSelector`` objects)

* dealing with unexpectedly bad input data:

  * ``from_json`` variant/option which scrubs data which fails in any
    way, returning objects which could be parsed and left-over JSON
    which couldn't be parsed.

  * support for polymorphic JSON, either through a flag field (special
    field is mapped to type) or via subclass duck-typing (subclass is
    selected automatically based on keys seen on input)

* collections:

  * complete ``KeyedCollection``: __delitem__, __contains__

  * complete ``ListCollection``: extend, __getslice__, etc; get rid of
    ``ListRecord`` completely.

  * implement ``DictCollection``

  * implement ``SetCollection``

  * enhance Collection types to type-check items on append, etc

* property traits for basic XML marshal support (in case the 90's
  calls and wants to send us some data)

* the diff iterator could notice if items have moved keys in a
  collection and emit a MOVED or RENAMED ``DiffInfo``

* refactor all the ugly ``if isinstance(x, Y):`` blocks to use
  ``simplegeneric`` instead

* provide a collection of ready-made typed properties; this will
  probably involve changing the way that property types are
  distinguished and selected

* avro marshaling

* property traits for schema systems which number attributes, to
  support thrift


Untested cases
--------------

The following cases are known to be missing tests:

* ``from_json`` with ``ListRecord``

* Test marshaling out classes which define ``to_json()``, with and
  without the ``extraneous`` parameter.

* ``JsonRecord`` and ``JsonProperty`` are largely untested;

  * test cases for ``json_in`` and ``json_out`` transform functions
  * check ``json_name=None`` suppresses marshal out via JSON
  * using ``from_json`` with json strings (not JSON data)
  * double-check setting ``extraneous`` makes

* test case for sub-classing property types to provide ``isa=`` in a way
  that might be more natural for some folk; this should work (after all,
  it works for ``ListProperty``), but it should be tested

* iteration over Records; I've been reluctant to test this because I
  believe that the API is not very pythonic.  An API like schematics'
  ``.atoms()`` would be cleaner IMHO.

* ``SafeCollectionProperty`` is untested

* required, but lazy attributes

* ``del record.property`` and ``record.property = None``

* ``FieldSelector`` with ``None`` components indicating "all members of a
  collection"

* ``MultiFieldSelector`` unspecifically needs more tests, because
  parts of its recursive constructor aren't reached that I thought
  should be by its test case.  They should be reached, or the code
  simplified.

* Untested Exception Paths:

  * bad combinations of attribute traits
  * ``DiffInfo`` made with missing field selector properties
  * mis-use of ``ListProperty``
  * multiple inheritance between ``Record`` types defining clashing
    properties
