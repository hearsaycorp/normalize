Normalize changelog and errata
==============================

1.0.0 28th September 2015
-------------------------
As a hint to the stability of the code, I've decided to call this
release 1.0.

But with a major version comes a major new feature.  The 0.x approach
was one of type safety and strictness.  The 1.0 approach will be one
of convenience and added pythonicity, layered on top of an inner
strictness.  To allow for backwards compatibility, in general you must
specify the new behavior in the class declaration.

The details will be documented in the manual, tests and tutorial, but
in a nutshell, the new features are:

* unset V1 attributes return something false (usually ``None``)
  instead of ``AttributeError``.  You can override the type of
  ``None`` returned with ``v1_none=''``.  This value can be assigned
  to the slot, and if it doesn't pass the type constraint, instead of
  raising ``normalize.exc.CoercionError`` it will behave the same as
  deleting the attribute.

* there's a new base class called ``AutoJsonRecord`` which allows you
  to access attributes of the input JSON, previously accessed via
  ``.unknown_json_keys['attribute']``, by regular attribute access.
  This feature is recursive, so you can quickly work with new APIs
  without having to pre-write a bunch of API definitions.

* Much more is available via a direct ``from normalize import Foo``,
  including all of the typed property declarations, the visitor API,
  and diff types.

* ``DatetimeProperty`` and ``DateProperty`` now ship with a
  ``json_out`` function which uses ``isoformat()`` to convert to a
  string as you'd expect them to.

* New type ``NumberProperty`` which will hold any numeric type (as
  decided by ``numbers.Number``)

* FieldSelector got a new function ``get_or_none`` which is like
  ``get`` but returns ``None`` instead of throwing a
  ``FieldSelectorException``.

There are also some minor backwards incompatibilities:

* setting ``default=None`` (or any other false, immutable value) on a
  property will select a V1 property.  The benefit of this is it makes
  the class instance dictionary lighter, for classes which specify a
  lot of ``default=None`` or ``default=''`` properties.

* ``DateTimeProperty`` now ships with default JSON IO functions which
  use ``datetime.datetime.strptime`` and
  ``datetime.datetime.isoformat()`` to convert to and from a string.
  This is an improvement, but technically an API change you might need
  to consider if you were expecting it to fail.

* ``DateProperty`` will now force the value type to be a date, and
  will truncate datetimes to dates as originally envisioned.

* ``StringProperty`` and ``UnicodeProperty`` no longer will convert
  anything you pass to them to a string or unicode string.  This is
  actually a new feature, because before the declaration was unusable;
  just about everything in python can be converted to a string, so
  you'd end up with string representations of objects in the slots.
  Now you get type errors.

* The ``empty`` property parameter has been removed completely.

0.10.0 21st August 2015
-----------------------
* Exceptions raised while marshalling JSON are now wrapped by a new
  exception which exposes the path within the input document that the
  problem occurred.

* Various structured exceptions had attribute names changed.  They're
  now more consistent across varying exception types.

* Using ``JsonListProperty()`` makes the type of the inner collection
  a ``JsonRecordList`` subclass instead of previously it was a
  ``RecordList``, enabling the context above.  Beware that this has
  implications to input marshalling; previously skipped marshalling
  will now be called.

* When using ``JsonListProperty``, previously if it encountered a
  different type of collection (or even a string), it would build with
  just the keys.  This now raises an exception.  Similarly with
  ``JsonDictProperty`` if you pass something other than a mapping.

* Field selectors with upper case and digits in attribute names will
  be converted to paths via ``.path`` without using quoting if they
  are valid JavaScript/C tokens.

0.9.10 9th July 2015
--------------------
* the implicit squashing of attributes which coerce to None now also
  works for subtype coerce functions

0.9.9 8th July 2015
-------------------
* added a new, convenient API for creating type objects which check
  their values against a function: ``subtype``

  For example, if you want to say that a slot contains an
  ISO8601-formatted datetime string, you could declare that like this:

  ::

      import re

      import dateutil.parser
      import normalize

      # simplified for brevity
      iso8601_re = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.(\d+))?$')

      ISO8601 = normalize.subtype(
           "ISO8601", of=str,
           where=lambda x: re.match(iso8601_re, x),
           coerce=lambda s: dateutil.parser.parse(s).isoformat(),
      )

      class SomeClass(normalize.Record):
          created = normalize.Property(isa=ISO8601)

0.9.8 26th June 2015
--------------------
* MultiFieldSelector.from_path(path) did not work if the 'path' did not
  end with ')' (ie, there was only one FieldSelector within).

* FieldSelector delete operations were updated to work with collection
  items: previously, you could not remove items from collections, or
  use 'None' at the end of a delete Field Selector.  This now works for
  DictCollection and ListCollection.

* Some bugs with FieldSelector.post, .put and .delete on DictCollections
  were cleaned up.

* It is now possible to use FieldSelector.post(x, y) to create a new
  item in a collection or set a property specified as a record where 'x' is
  the only required property.

0.9.7 9th June 2015
-------------------
* the fix delivered by 0.9.6 fix now also fixes empty collections

0.9.6 9th June 2015
-------------------
* fixed regression introduced in 0.9.4 with collections, which cleanly round
  trip using a non-specialized VisitorPattern again

0.9.5 9th June 2015
-------------------
* FieldSelector and MultiFieldSelector's operations now work with
  DictCollection containers as well as native dict's

0.9.4 5th June 2015
-------------------
* Fixed normalize.visitor for collections of non-Record types as well.

0.9.3 3rd June 2015
-------------------
* Comparing simple collections will now return MODIFIED instead of
  ADDED/REMOVED if individual indexes/keys changed

* Comparing typed collections where the item type is not a Record type
  (eg ``list_of(str)``) now falls back to the appropriate 'simple'
  collection comparison function.  This works recursively, so you can
  eg get meaningful results comparing ``dict_of(list_of(str))``
  instances.

* New diff option 'moved' to return a new diff type MOVED for items in
  collections.

* the completely undocumented ``DiffOptions.id_args`` sub-class API
  method is now deprecated and will be removed in a future release.

* Specifying 'compare_filter' to diffs over collections where the
  field selector matches something other than the entire collection
  now works.

0.9.2 27th May 2015
-------------------
* Another backwards compatibility accessor for ``RecordList.values``
  allows assignment to proceed.

  ::

      class MyFoo(Record):
          bar = ListProperty(of=SomeRecord)

      foo = MyFoo(bar=[])

      # this will now warn instead of throwing Exception
      foo.bar.values = list_of_some_records

      # these forms will not warn:
      foo.bar = list_of_some_records
      foo.bar[:] = list_of_some_records

0.9.1 22nd May 2015
-------------------
* the ``RecordList.values`` removal in 0.9.0 has been changed to be a
  deprecation with a warning instead of a hard error.

0.9.0 21st May 2015
-------------------
* ``ListProperty`` attribute can now be treated like lists; they
  support almost all of the same methods the built-in ``list`` type
  does, and type-checks values inserted into them with coercion.

  *note*: if you were using ``.values`` to access the internal array,
  this is now not present on ``RecordList`` instances.  You should be
  able to just remove the ``.values``:

  ::

      class MyFoo(Record):
          bar = ListProperty(of=SomeRecord)

      foo = MyFoo(bar=[somerecord1, somerecord2])

      # before:
      foo.bar.values.extend(more_records)
      foo.bar.values[-1:] = even_more_records

      # now:
      foo.bar.extend(more_records)
      foo.bar[-1:] = even_more_records

* ``DictProperty`` can now be used, and these also support the
  important ``dict`` methods, with type-checking.

* You can now construct typed collections using ``list_of`` and
  ``dict_of``:

  ::

     from normalize.coll import list_of, dict_of

     complex = dict_of(list_of(int))()
     complex['foo'] = ["1"]  # ok
     complex['foo'].append("bar")  # raises a CoercionError

  Be warned if using ``str`` as a type constraint that just about
  anything will happily coerce to a string, but that might not be what
  you want.  Consider using ``basestring`` instead, which will never
  coerce successfully.

0.8.0 6th March 2015
--------------------
* ``bool(record)`` was reverted to pre-0.7.x behavior: always True,
  unless a Collection in which case Falsy depending on the number of
  members in the collection.

* Empty psuedo-attributes now return ``normalize.empty.EmptyVal``
  objects, which are always ``False`` and perform a limited amount of
  sanity checking/type inference, so that misspellings of sub-properties
  can sometimes be caught.

0.7.4 5th March 2015
--------------------
* A regression which introduced subtle bugs in 0.7.0, which became more
  significant with the new feature delivered in 0.7.3 was fixed.

* An exception with some forms of dereferencing MultiFieldSelectors was
  fixed.

0.7.3 4th March 2015
--------------------
* Added a new option to diff to suppress diffs found when comparing
  lists of objects for which all populated fields are filtered.

0.7.2 27th February 2015
------------------------
* Fixed a regression with the new 'json_out' behavior I decided was big
  enough to pull 0.7.1 from PyPI for.

0.7.1 27th February 2015
------------------------
* VisitorPattern.visit with visit_filter would not visit everything in
  the filter due to the changes in 0.7.0

* MultiFieldSelector subscripting, where the result is now a "complete"
  MultiFieldSelector (ie, matches all fields/values) is now more
  efficient by using a singleton

* the return of 'json_out' is no longer unconditionally passed to
  ``to_json``: call it explicitly if you desire this behavior:

  ::

      class Foo(Record):
          bar = Property(isa=Record, json_out=lambda x: {"bar": x})

  If you are using ``json_out`` like this, and expecting ``Record``
  values or anything with a ``json_data`` method to have that called,
  then you can wrap the whole thing in ``to_json``:

  ::

      from normalize.record.json import to_json

      class Foo(Record):
          bar = Property(isa=Record, json_out=lambda x: to_json({"bar": x}))

0.7.0 18th February 2015
------------------------
Lots of long awaited and behavior-changing features:

* empty pseudo-attributes are now available which return (usually falsy)
  values when the attribute is not set, instead of throwing
  AttributeError like the regular getters.

  The default is to call this the same as the regular attribute, but
  with a '0' appended;

  ::

      class Foo(Record):
          bar = Property()

      foo = Foo()
      foo.bar  # raises AttributeError
      foo.bar0  # None

  The default 'empty' value depends on the passed ``isa=`` type
  constraint, and can be set to ``None`` or the empty string, as
  desired, using ``empty=``:

  ::

      class Dated(Record):
          date = Property(isa=MyType, empty=None)

  It's also possible to disable this functionality for particular
  attributes using ``empty_attr=None``.

  Property uses which are not safe will see a new warning raised which
  includes instructions on the changes recommended.

* accordingly, bool(record) now also returns false if the record has no
  attributes defined; this allows you to use '0' in a chain with
  properties that are record types:

  ::

      if some_record.sub_prop0.foobar0:
          pass

  Instead of the previous:

  ::

      if hasattr(some_record, "sub_prop") and \
              getattr(some_record.sub_prop, "foobar", False):
          pass

  This currently involves creating a new (empty) instance of the object
  for each of the intermediate properties; but this may in the future be
  replaced by a proxy object for performance.

  The main side effect of this change is that this kind of code is no
  longer safe:

  ::

      try:
          foo = FooJsonRecord(json_data)
      except:
          foo = None 

      if foo:
          #... doesn't imply an exception happened

* The mechanism by which ``empty=`` delivers psuedo-attributes is
  available via the ``aux_props`` sub-class API on Property. 

* Various ambiguities around the way MultiFieldSelectors and their ``__getattr__``
  and ``__contains__`` operators (ie, ``multi_field_selector[X]`` and ``X in
  multi_field_selector``) are defined have been updated based on
  findings from using them in real applications.  See the function
  definitions for more.


0.6.6 16th January 2014
-----------------------
* Fix ``FieldSelector.delete`` and ``FieldSelector.get`` when some of
  the items in a collection are missing attributes

0.6.5 2nd January 2014
----------------------
* lazy properties would fire extra times when using visitor APIs or
  other direct use of __get__ on the meta-property (#50)

0.6.4 2nd January 2014
----------------------
* The 'path' form of a multi field selector can now round-trip, using
  ``MultiFieldSelector.from_path``
* Two new operations on ``MultiFieldSelector``: ``delete`` and
  ``patch``

0.6.3 30th December 2014
------------------------
* Add support in to_json for marshaling out a property of a record
* The 'path' form of a field selector can now round-trip, using
  ``FieldSelector.from_path``

0.6.2 24rd September 2014
-------------------------
* A false positive match was fixed in the fuzzy matching code.

0.6.1 23rd September 2014
-------------------------
* Gracefully handle unknown keyword arguments to Property()
  previously this would throw an awful internal exception.

* Be sure to emit NO_CHANGE diff events if deep, fuzzy matching found no
  differences

0.6.0 17th September 2014
-------------------------
* Diff will now attempt to do fuzzy matching when comparing
  collections.  This should result in more fine-grained differences
  when comparing data where the values have to be matched by content.
  This implementation in this version can be slow (O(N²)), if comparing
  very large sets with few identical items.

0.5.5 17th September 2014
-------------------------
* Lots of improvements to exceptions with the Visitor

* More records should now round-trip ('visit' and 'cast') cleanly with
  the default Visitor mappings; particularly ``RecordList`` types with
  extra, extraneous properties.

* ListProperties were allowing unsafe assignment; now all collections
  will always be safe (unless marked 'unsafe' or read-only)

0.5.4 20th August 2014
----------------------
* values in attributes of type 'set' get serialized to JSON as lists
  by default now (Dale Hui)

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
