
An introduction to using ``normalize``
======================================

This introduction is designed to first familiarize you with how "pure"
``normalize`` Records work.  This core behavior is important to learn,
as it will avoid surprises later.

It is not normally the way of python to labor over object definitions
and type declarations.  But it is these definitions that drive the
useful applications of the module: converting to and from JSON, deep
object comparison, etc.

Thankfully, very little is compulsory, for instance most of the time
you probably don't really need to declare what type a field is.  The
default JSON marshall in function ignores unknown keys, so you can
also just declare the keys you care about extracting.

This tutorial should help you see the purpose of the various parts of
the declaration API, so that you can write your classes in minimal,
pythonic style.

Basic Records and Properties
----------------------------

``normalize`` is built around two core concepts: records, and
properties.

To start, declare a class, based off ``Record``, and its properties:

  ::

      from normalize import Property, Record

      class Star(Record):
          hip_id = Property(isa=int, required=True)
          name = Property(isa=str)
          spectral_type = Property(isa=str)

Once you have done this, you can create instances in a hopefully
unsurprising way:

  ::

      >>> maia = Star(hip_id=17573,
                      name="maia",
                      spectral_type="B8III")
      >>> maia
      Star(hip_id=17573, name='maia', spectral_type='B8III')
      >>> eval(repr(maia)) == maia
      True
      >>>

You can also construct from ``dict`` objects and other objects which
implement ``collections.Mapping`` to a sufficient level:

  ::

      >>> maia = Star({"hip_id": 17573,
                       "name": "maia"})
      >>>

One of the things that distinguishes ``normalize`` from other similar
libraries is that it supports **type information** on properties,
along with **constraints**.  These are not required, but allow some
useful applications, such as validation and marshalling.  They also
allow programming mistakes to be discovered earlier, by throwing an
error when the first incorrect assignment is made, rather than later.

The ``hip_id`` property was declared to be *required*, so
unsurprisingly, if you try to create an object without it, you get an
exception:

  ::

      >>> Star()
      ValueError: Star.hip_id is required
      >>>

(for brevity, in this document, tracebacks will be omitted from the
python interpreter output).

In addition to marking properties as ``required``, you can pass a
*check* function, which must return something true-ish for the value
to pass:

  ::

      >>> class Star(Record):
             hip_id = Property(isa=int, required=True,
                               check=lambda x: 0 < x < 120000)
             name = Property(isa=str)
             spectral_type = Property(isa=str)

      >>> Star(hip_id=150000)
      ValueError: Star.hip_id value '150000' failed type check


For instance, if we put a string into the ``hip_id`` field, then we
can expect an error:

  ::

      >>> maia.hip_id = "HIP17573"
      ValueError: invalid literal for int() with base 10: 'HIP17573'
      >>> 

Unless, that is, the value is accepted by the ``int`` constructor:

  ::

      >>> maia.hip_id = "17573"
      >>> maia.hip_id
      17573
      >>> 

What happened was that the passed value did not satisfy the type
constraint (ie, the type passed to ``isa``).  So, the descriptor
started *coercion*.

.. note::

   Adding any of the three *type constraint* options to a Property
   (``isa=``, ``required=``, or ``check=``) automatically mixes in the
   'safe' trait, turning your ``Property`` into a ``SafeProperty`` via
   the facility described in :ref:`meta`.  This ensures that any rules
   you specify for assignment to an attribute are also caught by
   assignment to that attribute.

.. _coercion:

Property Type Coercion
----------------------

Whenever a value is set in a property (either during initial
construction or when the attribute is assigned), the type is checked
to be type safe according to its definition.  The rules are:

1. **is** the value being assigned of the right type already?

   This is basically (literally) ``isinstance(value, isa)`` (where
   ``isa`` was the value you passed to ``isa=`` in the ``Property``
   declaration). If so, then *the coerce function is not called*
   because the value is already considered to be of the correct type.

   You can pass a tuple of types to ``isa=``, as well.  For a while,
   this worked entirely by accident.  But it has a good basis in type
   theory as a *type union*, so this happy accident is part of the
   formal API.

   If you didn't declare anything to ``isa=``, then *any* value (even
   ``None``) gets a pass here.  If you want to explicitly allow
   ``None`` as a value, then you must use a tuple which includes
   ``types.NoneType``.  Otherwise, you can expect the declared type or
   ``AttributeError`` when you access the attribute.

2. If the value is not already of the right type, try to **coerce** it.

   Each property has a coerce function for dealing with malfeasant
   values.  If you specified ``isa=``, then the default is the type,
   because in Python, types are also constructors.  This can lead to
   some confusion; see the gotcha section later in this introduction.

   For people coming from Perl's Moose, this is one area where the
   design is a bit different in how you construct your classes, but
   ultimately it is equivalent in functionality.

3. Once the value is of the right type, then **check** it is valid using
   any declared ``check=`` function.

   Most of the time you probably don't need to bother with this, but
   it is there if you need it.

   Note that the check method is called *after* type coercion, and it
   is *always* called when a property is set: either during
   construction or later by assignment.
   If an object is constructed without the property, then it is *not*
   called.

So, let's go back to our example.  Let's extend the definition with a
``check`` function and a custom ``coerce`` method:

  ::

      def fix_id(val):
          if isinstance(val, basestring) and val.upper().startswith("HIP"):
              return int(val.upper().lstrip("HIP "))
          else:
              return int(val)


      class Star(Record):
          hip_id = Property(isa=int, required=True,
                            coerce=fix_id,
                            check=lambda i: 0 < i < 120000)
          name = Property(isa=str)
          spectral_type = Property(isa=str)

Now, it's perfectly fine to pass a value including the prefix:

  ::

      >>> maia = Star(hip_id="hip17573")
      >>> maia.hip_id
      17573
      >>> 

But if we pass an unreasonable ID, it fails:

  ::

      >>> maia.hip_id = 175373
      ValueError: Star.hip_id value '175373' failed type check
      >>> maia.hip_id = "hip175373"
      ValueError: Star.hip_id value '175373' failed type check
      >>> maia.hip_id = "hop175373"
      ValueError: invalid literal for int() with base 10: 'hop175373'
      >>> maia.hip_id = None
      TypeError: int() argument must be a string or a number, not 'NoneType'
      >>>

The first two examples failed because they failed the ``check``
function.  The second failed *after* type coercion, so the invalid
value in the exception is the coerced value, not the original value.
The third and fourth examples threw exceptions inside the ``coerce``
function.

.. _defaults:

Property Defaults
-----------------

It's possible to pass a value or function to the ``default=``
parameter, to set a default value for a property in case one is not
provided.

You can even use this to make properties that do not raise
``AttributeError`` if they were not set:

  ::

      >>> import types
      >>> class Sloppy(Record):
              anything = Property(default=None)
              goes = Property(default='')
              here = Property(default=None, isa=(types.NoneType, int))

      >>> slop = Sloppy()
      >>> slop
      Sloppy(anything=None, goes='', here=None)
      >>>

Beware that the value is assigned without consideration about whether
it needs to be copied or not.  For immutable value types like strings,
integers, etc this is fine.  For mutable lists, dictionaries, etc, it
is likely to be a problem if you want to change the value after
construction.  An easy way around this is to supply a function that
returns a new instance of the value:

  ::

      >>> class Foo(Record):
      ...   bar = Property(default=lambda: [])
      ...
      >>> Foo()
      Foo(bar=[])
      >>>


Lazy Evaluation
---------------

There is some relatively limited support for lazy evaluation in this
module.  It's hardly lazy to the extent of, say, Haskell, where the
compiler will defer all execution not required for IO.  But, it does
let you declare properties whose value depends on other properties.

For example:

  ::

      import astrolib.coords as C

      class Star(Record):
          hip_id = Property(isa=int, required=True)
          name = Property(isa=str)
          right_ascention = Property(isa=float)
          declination = Property(isa=float)

          def make_position(self):
              return C.Position((self.right_ascention, self.declination))

          position = Property(isa=C.Position,
                              lazy=True, default=make_position)

When first constructed, the Record has no ``position``:

  ::

      >>> tcent = Star(hip_id=68933, name="Menkent",
                       right_ascention=226.67, declination=-36.367)
      >>> tcent
      Star(declination=-36.367, hip_id=68933, name='Menkent', right_ascention=226.67)
      >>>

However, if the ``position`` property is read, it now has that property:

  ::

      >>> tcent.position
      226.670000 -36.367000 (degrees)
      >>> tcent
      Star(declination=-36.367, hip_id=68933, name='Menkent', position=226.670000 -36.367000 (degrees), right_ascention=226.67)
      >>>

Most of the time, you don't really need lazy properties, because you
can just write ``@property`` methods on the class for python users.
However, they are the only way to provide a ``default`` which is an
instance method, and depends on other attributes.

Lazy properties are also useful when writing properties which
logically exist when marshaling data out, but are derived from
multiple object property fields.  (it isn't currently possible to do
this without storing the return value in the object, or sub-classing
``Property``; patches welcome)

Properties which are Records
----------------------------

With nesting of data types, ``normalize`` starts to become more than
just the gimmicks shown so far.

  ::

      class Binary(Record):
          name = Property(isa=str)
          primary = Property(isa=Star)
          secondary = Property(isa=Star)

Now, it is possible to construct a more complicated object:

  ::

      >>> cyg = Binary(name="61 Cygni",
                       primary=Star(hip_id=104214),
                       secondary=Star(hip_id=104217))
      >>> cyg
      Binary(name='61 Cygni', primary=Star(hip_id=104214), secondary=Star(hip_id=104217))
      >>>

This also works when using the ``dict`` constructor:

  ::

      >>> cyg2 = Binary({"name": "61 Cygni",
                         "primary": {"hip_id": 104214},
                         "secondary": {"hip_id": 104217}})
      >>> cyg == cyg2
      True
      >>>

Properties which are Lists of Records
-------------------------------------

It's also possible to make properties which are lists of records:

  ::

      from normalize import ListProperty

      class StarSystem(Record):
          name = Property(isa=str)
          components = ListProperty(of=Star)

Now, we can construct objects with a number of sub-records in them.

  ::

      >>> acent = StarSystem(name="Alpha Centauri")
      >>> acent.components = ({"name": "Alpha Centauri A", "hip_id": 71683},
                              {"name": "Alpha Centauri B", "hip_id": 71681},
                              {"name": "Alpha Centauri C", "hip_id": 70890})
      >>> acent
      StarSystem(components=StarList([Star(hip_id=71683, name='Alpha Centauri A'), Star(hip_id=71681, name='Alpha Centauri B'), Star(hip_id=70890, name='Alpha Centauri C')]), name='Alpha Centauri')
      >>>

If you look closely at the created object, there's a type
``StarList``.  This was created as side effect of making a
``ListProperty(of=Star)``.  It's a subclass of ``RecordList``, and
supports most of the ``LISTMETHODS``.  In general, you should be able
to treat it like a standard ``list``, though there might be some
methods not yet implemented.

It's possible to create these list types as the actual collection type
of a property by passing it as a ``coll=`` parameter; as in:

  ::

      class StarList(RecordList):
          itemtype = Star

      class StarSystem(Record):
          name = Property(isa=str)
          components = ListProperty(of=Star, coll=StarList)

This is mostly useful if you add properties or methods to the
container itself.

In this situation, use of ``ListProperty`` is largely redundant.  You
could also just use ``Property(isa=StarList)``


Referring to fields within Records
----------------------------------

There is a class, ``FieldSelector``, which allows you to select
individual properties from a record:

  ::

     >>> from normalize import FieldSelector
     >>> name = FieldSelector(["name"])
     >>> name.get(acent)
     'Alpha Centauri'
     >>> name.get(acent.components[1])
     'Alpha Centauri B'
     >>> FieldSelector(["components", 2, "hip_id"]).get(acent)
     70890
     >>>

You can also use ``None`` as a wildcard, if the component at the path
is a collection such as a list:

  ::

      >>> FieldSelector(['components', None, "hip_id"]).get(acent)
      [71683, 71681, 70890]
      >>>

You can also put values in the data structure, and even add new items
to collections in this way:

  ::

      >>> name.put(acent, "Rigil Kent")
      >>> FieldSelector(['components', 3, 'hip_id']).post(1234)
      ValueError: Star.hip_id is required
      >>> FieldSelector(['components', 3]).post({"hip_id": 1234})
      TypeError: 'StarList' object does not support item assignment
      >>>

Yes, well.  It doesn't interact well with required attributes,
clearly.  And that comment above about the incompleteness of
``RecordList`` is evident.  One day soon hopefully!

There's also the ``MultiFieldSelector``, which can be used to 'filter'
properties:

  ::

      >>> from normalize.selector import MultiFieldSelector
      >>> MultiFieldSelector(['components', None, "hip_id"]).get(acent)
      StarSystem(components=StarList([Star(hip_id=71683), Star(hip_id=71681), Star(hip_id=70890)]))
      >>>

This class can take multiple paths, and will return the intersection
of all of the fields listed.

Comparing object structures
---------------------------

With two objects of the same type, you can compare them to see what
fields are different:


  ::

      >>> maia = Star(hip_id=17573,
                      name="maia")
      >>> maia2 = Star(hip_id=17573,
                       name="20 Tauri",
                       spectral_type="B8III")
      >>> for diff in maia.diff(maia2):
              print diff
      <DiffInfo: MODIFIED .name>
      <DiffInfo: ADDED .spectral_type>
      >>>

Each item in the returned ``Diff`` object has two ``FieldSelector``
objects which refer to where in the passed-in object structures the
field that changed was (or wasn't, in the case of ADDED or REMOVED
diffs).

This comparison supports a number of comparison options, such as
whether to normalize whitespace and unicode normal form (on by
default) or whether to distinguish between an attribute set to an
empty string, and no attribute set at all.

It's also possible to compare against object structures which are not
``Record`` classes at all:

  ::

      >>> from schematics.models import Model
      >>> from schematics.types import IntType, StringType
      >>> class Starmatic(Model):
              hip_id = IntType(required=True)
              name = StringType()
              spectral_type = StringType()
      >>> maia3 = Starmatic({"hip_id": 17573,
                             "name": "20 Tauri"})
      >>> for diff in maia.diff(maia3, duck_type=True):
              print diff
      <DiffInfo: MODIFIED .name>
      <DiffInfo: ADDED .spectral_type>
      >>>

Naturally, this "duck typing" diff is only comparing properties
defined in the ``normalize`` class.  This functionality is useful for
those transitioning from other similar systems or ad-hoc classes.

Collections and primary keys
----------------------------

When comparing collections, special behavior happens.  In order to be
able to tell the difference between a member in a collection being
removed and replaced by a new one, or merely having a single field
changed, ``normalize`` must know which of its fields uniquely identity
it.

So, if we use the definitions:

  ::

      from normalize import ListProperty, Property, Record, RecordList

      class Star(Record):
          hip_id = Property(isa=int, required=True)
          primary_key = [hip_id]
          name = Property(isa=str)
          spectral_type = Property(isa=str)

      class StarList(RecordList):
          itemtype = Star

Then there can be a sensible comparison:

  ::

      >>> acent = StarList([Star(hip_id=71683, name='Alpha Centauri A'),
                            Star(hip_id=71681, name='Alpha Centauri B'),
                            Star(hip_id=70890, name='Alpha Centauri C')])
      >>> acent_ab = StarList([
              {"hip_id": "71683", "name": 'Alpha Centauri A',
               "spectral_type": 'G2 V'},
              {"hip_id": "71681", "name": 'Alpha Centauri B',
               "spectral_type": 'K1 V'},
          ])
      >>> for diff in acent.diff(acent_ab):
              print diff
      <DiffInfo: REMOVED [2]>
      <DiffInfo: ADDED [1].spectral_type>
      <DiffInfo: ADDED [0].spectral_type>
      >>>

Without this ``primary_key``, the diff mechanism would only be able to
match entries in the collection if *all* of their properties are
identical:

  ::

      >>> acent = StarList([Star(hip_id=71683, name='Alpha Centauri A'),
                            Star(hip_id=71681, name='Alpha Centauri B'),
                            Star(hip_id=70890, name='Alpha Centauri C')])
      >>> acent_ab = StarList([
              {"hip_id": "71683", "name": 'Alpha Centauri A'},
              {"hip_id": "71681", "name": 'Alpha Centauri B',
               "spectral_type": 'K1 V'},
          ])
      >>> for diff in acent.diff(acent_ab):
              print diff
      <DiffInfo: REMOVED [2]>
      <DiffInfo: REMOVED [1]>
      <DiffInfo: ADDED [1]>
      >>>

You can also get in trouble if you have properties which end up being
non-hashable types (eg, an unparsed ``dict``).  These may throw errors
when compared due to unhashability.

Marshaling to and from JSON
---------------------------

You can convert any ``Record`` to JSON using ``normalize.to_json``:

  ::

      >>> from normalize import from_json, to_json
      >>> to_json(acent)
      [{'hip_id': 71683, 'name': 'Alpha Centauri A'}, {'hip_id': 71681, 'name': 'Alpha Centauri B'}, {'hip_id': 70890, 'name': 'Alpha Centauri C'}]
      >>> to_json(MultiFieldSelector([None, "hip_id"]).get(acent))
      [{'hip_id': 71683}, {'hip_id': 71681}, {'hip_id': 70890}]
      >>> 

Note that it returns JSON data structures, which can be then passed to
``json.dumps`` or an equivalent function.

You can also convert back the other way using ``from_json`` (supports
JSON strings or JSON data):

  ::

      >>> from_json(Star, {'hip_id': 71683, 'name': 'Alpha Centauri A'})
      Star(hip_id=71683, name='Alpha Centauri A')
      >>>

If your classes derive ``JsonRecord``, then the API gets even more
convenient:

  ::

      >>> class JsonStar(Star, JsonRecord):
              pass
      >>> js = JsonStar('{"hip_id": 71683, "name": "Alpha Centauri A"}')
      >>> js
      JsonStar(hip_id=71683, name='Alpha Centauri A')
      >>> js.json_data()
      {'hip_id': 71683, 'name': 'Alpha Centauri A'}
      >>>

Customizing JSON Conversion
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Frequently, you have types which are not supported by the JSON data
model.  These properties need conversion functions for the
transformation.

Revisiting the earlier example with a C library type, this might look
like this:

  ::

      import astrolib.coords as C
      from normalize import Record, Property
      class Star(Record):
          hip_id = Property(isa=int, required=True)
          name = Property(isa=str)
          right_ascention = Property(isa=float, json_name=None)
          declination = Property(isa=float, json_name=None)
          def make_position(self):
              return C.Position((self.right_ascention, self.declination))
          position = Property(isa=C.Position,
                              lazy=True, default=make_position,
                              json_out=lambda x: x.hmsdms())

Now, this type will round-trip to JSON:

  ::

      >>> from normalize import from_json, to_json
      >>> tcent = Star(hip_id=68933, name="Menkent",
                       right_ascention=226.67, declination=-36.367)
      >>> to_json(tcent)
      {'position': '15:06:40.800 -36:22:01.200', 'hip_id': 68933, 'name': 'Menkent'}
      >>> from_json(Star, {'position': '15:06:40.800 -36:22:01.200', 'hip_id': 68933, 'name': 'Menkent'})
      Star(hip_id=68933, name='Menkent', position=15h 6m 40.800s -36d 22m 1.200s (degrees))
      >>>

There's a couple of things to note in this.

First, practically: setting ``json_name`` to ``None`` supresses the
attribute from being marshalled to and from JSON.

Secondly: ``JsonProperty`` arguments were passed to the ``Property``
constructor.  Instead of ``Property`` failing, it looked to see what
property types it knew of which supported that constructor argument,
and created one of those instead.

Custom Visitor Classes
----------------------

It's trivial to write a *visitor* which applies a custom function to
every *value* and *reduces* the compound results back into a single
return value, using ``normalize.visitor.Visitor``:

  ::

        from normalize.visitor import Visitor

        JSON_CAN_DUMP = (basestring, int, long, dict, list)

        class SimpleDumper(Visitor):
            def apply(self, value, *args):
                if isinstance(value, JSON_CAN_DUMP):
                    dumpable = value
                elif isinstance(value, datetime):
                    dumpable = value.isoformat()
                else:
                    raise Exception("Can't dump %r" % value)
                return dumpable

This class is now somewhat similar to ``to_json``, except that it
ignores all the ``json_*`` options that were passed to the
``Property`` field.

  ::

      >>> SimpleDumper().map(acent)
      {'name': 'Alpha Centauri',
             'components': [{'hip_id': 71683, 'name': 'Alpha Centauri A'},
                            {'hip_id': 71681, 'name': 'Alpha Centauri B'},
                            {'hip_id': 70890, 'name': 'Alpha Centauri C'}]}
      >>>

I'd like to now proudly state that all of the visitor pattern
functions in this module are implemented on top of this ``Visitor``
class.  But, sadly, that is simply not true, yet.

Gotchas
-------

This section has some notes based on some first impressions from early
adopters that I think are noteworthy.

* unintended successful coercion

  You'd better make sure that you don't set a ``None`` default without
  adding ``types.NoneType`` to your ``isa=`` type constraint.  Some
  types, after all, quite happily coerce from ``None``:

  ::

      >>> class Sloppy(Record):
              anything = Property(isa=str, default=None)

      >>> slop = Sloppy()
      >>> slop.anything
      'None'
      >>>

  See :ref:`defaults` above for a version which allows ``None``,
  change your program to trap ``AttributeError`` for an unset
  attribute or mark it as ``required=True`` if that suits the problem
  better.

* confusing, unsuccessful coercion

  Some types don't have a very flexible default constructor.  Take,
  for instance, ``datetime.datetime``:

    ::

        from datetime import datetime

        class DatedObject(Record):
            timestamp = Property(isa=datetime)

  When you construct it using a string, it throws this fantastic and
  useful exception:

    ::

        >>> DatedObject(timestamp="2012-12-25T12:00")
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
          File "normalize/record/__init__.py", line 28, in __init__
            meta_prop.init_prop(self, val)
          File "normalize/property/__init__.py", line 101, in init_prop
            obj.__dict__[self.name] = self.type_safe_value(value)
          File "normalize/property/__init__.py", line 76, in type_safe_value
            value = self.coerce(value)
        TypeError: an integer is required
        >>> 

  What happened there is that (according to the :ref:`coercion` rules)
  the string value passed in did not pass ``isinstance(X, datetime)``
  and so was passed to the default coercion function: the ``datetime``
  constructor.  However, the ``datetime`` constructor expects multiple
  positional arguments, not a string.  So, it interpreted the first
  argument as an integer and failed without noticing that other
  required arguments were not present.

  You probably want to instead use a flexible conversion function like
  ``dateutil.parser.parse``:

    ::

        from datetime import datetime
        from dateutil.parser import parse

        class DatedObject(Record):
            timestamp = Property(isa=datetime, coerce=parse)

  Which works more like you expect:

    ::

        >>> DatedObject(timestamp="2012-12-25T12:00")
        DatedObject(timestamp=datetime.datetime(2012, 12, 25, 12, 0))
        >>> 

  There's one shipped with this module as
  :py:mod:`normalize.property.types.DatetimeProperty` which already
  does this.  Did I mention this module comes with ABSOLUTELY NO
  WARRANTY?  :-)  Patches and bug reports welcome.
