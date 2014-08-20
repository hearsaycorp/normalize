Normalize changelog and errata
==============================

0.5.3 20th August 2014
----------------------
* fixed a corner case with collection diff & filters (github issue #45)

* fixed ``Property(list_of=SomeRecordType)``, which should have worked
  like ``ListProperty(of=SomeRecordType)``, but didn't due to a bug in
  the metaclass.

0.5.2 5th August 2014
---------------------
* You can now pass an object method to ``compare_as=`` on a property
  definition.

* New sub-class API hook in ``DiffOptions``:
  ``normalize_object_slot``, which receives the object as well as the
  value.

* passing methods to ``default=`` which do not call their first
  argument 'self' is now a warning.

0.5.1 29th July 2014
--------------------
* Subscripting a MultiFieldSelector with an empty (zero-length)
  FieldSelector now works, and returns the original field selector.
  This fixed a bug in the diff code when the top level object was a
  collection.

0.5.0 23rd July 2014
--------------------
* normalize.visitor overhaul.  Visitor got split into a sub-class API,
  VisitorPattern, which is all class methods, and Visitor, the instance
  which travels with the operation to provide context.  Hugely backwards
  incompatible, but the old API was undocumented and sucked anyway.

0.4.x Series, 19th June - 23rd July 2014
----------------------------------------
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

* The 'ignore_empty_slots' diff option is now capable of ignoring empty
  records as well as None-y values.  This even works if the records
  are not actually None but all of the fields that have values are
  filtered by the DiffOptions compare_filter parameter.

* added Diffas property trait, so you can easily add
  'compare_as=lambda x: scrub(x)' for field-specific clean-ups specific
  to comparison.

* errors thrown from property coerce functions are now wrapped in
  another exception to supply the extra context.  For instance, the
  example in the intro will now print an error like:

      CoerceError: coerce to datetime for Comment.edited failed with
                   value '2001-09-09T01:47:22': datetime constructor
                   raised: an integer is required

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
