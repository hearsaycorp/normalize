
Normalize changelog and errata
==============================

0.4.x Series, 19th June - 2nd July 2014
---------------------------------------
* added support for comparing filtered objects; ``__pk__()`` object
  method no longer honored.  See ``tests/test_mfs_diff.py`` for
  examples

* MultiFieldSelector can now be traversed by indexing, and supports
  the ``in`` operator, with individual indices or FieldSelector
  objects as the member.  See ``tests/test_selector.py`` for examples.

* ``extraneous`` diff option now customizable via the ``DiffOptions``
  sub-class API.

* ``Diff``, ``JsonDiff`` and ``MultiFieldSelector`` now have more
  useful default stringification.

0.3.0, 30th May 2014
--------------------
* enhancement to diff to allow custom, per-field normalization of
  values before comparison

* Some inconsistancies in JSON marshalling in were fixed

0.2.x Series, 24th April - 27th May 2014
----------------------------------------
* the return value from ``coerce`` functions is now checked against
  the type constraints (``isa`` and ``check`` properties)

* added capability of Property constructor to dynamically mix variants
  as needed; Almost everyone can now use plain ``Property()``,
  ``ListProperty()``, or a shorthand typed property declaration (like
  ``StringProperty()``); other properties like ``Safe`` and ``Lazy``
  will be automatically added as needed.  Property types such as
  ``LazySafeJsonProperty`` are no longer needed and were savagely
  expunged from the codebase.

* ``SafeProperty`` is now only a safe base class for ``Property``
  sub-classes which have type constraints.  Uses of
  ``make_property_type`` which did not add type constraints must be
  changed to ``Property`` type, or will raise
  ``exc.PropertyTypeMixNotFound``

* bug fix for pickling ``JsonRecord`` classes

* filtering objects via ``MultiFieldSelector.get(obj)`` now works for
  ``JsonRecord`` classes.

* The ``AttributeError`` raised when an attribute is not defined now
  includes the full name of the attribute (class + attribute)

0.1.x Series, 27th March - 8th April 2014
-----------------------------------------
* much work on the diff mechanisms, results, and record identity

* records which set a tuple for ``isa`` now work properly on
  stringification

* semi-structured exceptions (``normalize.exc``)

* the collections 'tuple protocol' (which models all collections as a
  sequence of *(K, V)* tuples) was reworked and made to work with more
  cases, such as iterators and generators.

* Added ``DateProperty`` and ``DatetimeProperty``
