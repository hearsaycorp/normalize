
Normalize
=========

The normalize package is a class builder and toolkit most useful for
writing "plain old data structures" to wrap data from network sources
in python objects.

It is called "normalize", because it is focused on the first normal
form of relational database modeling.
This is the simplest and most straightforward level which defines what
are normally called "records".
A record is a defined collection of properties/attributes ("columns"),
where you know roughly what to expect in each property/attribute, and
can access them by some kind of descriptor (ie, the attribute name).
You can also use it as a general purpose declarative metaprogramming
framework, as it ships with an official meta-object-protocol (MOP) API
to describe this information, built on top of python's notion of
classes/types and descriptors and extended where necessary.

Put simply, you write python classes to describe your assumptions
about the data structures you're dealing with, feed in input data and
you get regular python objects back which have attributes which you
can use naturally.
Or, you get an error and find you have to revisit your assumptions.
You can then perform basic operations with the objects, such as make
changes to them and convert them back, or compare them to another
version using the rich comparison API.
You can also construct the objects 'natively' using regular python
keyword/value constructors or by passing a dict as the first argument.

It is very similar in scope to the 'remoteobjects' and 'schematics'
packages on PyPI, and may in time evolve to include all the features
of those packages.

While there is some notion of primary keys in the module, mainly for
the purposes of recognizing objects in collections for comparison,
higher levels of normalization are an exercise left to the
implementor.


Features
--------

* declarative API, which may optionally contain direct marshalling
  hints:

      class Star(Record):
          id = Property(isa=int, required=True)
          name = Property(isa=str)
          other_names = Property(json_name="otherNames")

  Type descriptions (``isa=``) are completely optional, but if given
  will be use for type checking and coercion.

* rich descriptor API (in ``normalize.property``), including the
  notions of not just 'required' and 'isa' type hints as shown above
  but also default functions, custom-type check functions, and
  coercion functions.

  It also sports an extensible attribute trait system, which adds more
  features via optional Property sub-classes, selected automatically,
  enabling:

  * lazy attributes which shortcut at the python core level once
    calculated (a somewhat underused python feature)

  * read-only attributes

  * type-safe attributes (i.e., that type-check on assign)

  * collection attributes (see below)

* coercion from regular python dictionaries or key=value (kwargs)
  constructor arguments

* conversion to and from JSON for all classes, regardless of whether
  they derive ``normalize.record.json.JsonRecord``, using the visitor
  pattern.  Support for custom functions for JSON marshall in and out.

* conversion to primitive python types via the pickle API
  (``__getnewargs__``)

* typed collections API with item coercion (currently, only lists are
  implemented):

      class StarSystem(Record):
          components = ListProperty(Star)

      alpha_centauri = StarSystem(
          components=[{id=70890, name="Proxima Centauri"},
                      {id=71683, name="Alpha Centauri A"},
                      {id=71681, name="Alpha Centauri B"}]
      )

* "field selector" API which allows for specification of properties
  deep into nested data structures;

      name_selector = FieldSelector("components", 0, "name")
      print name_selector.get(alpha_centauri)  # "Proxima Centauri"

* comparison API which returns differences between two Records of
  matching types.  Ability to mark properties as "extraneous" to skip
  comparison (this also affects the ``==`` operator)
