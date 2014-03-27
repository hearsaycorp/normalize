
======================================
the scope and purpose of ``normalize``
======================================

What's in a name?
-----------------

It is called "normalize", because what you do with it is akin to the
first normal form of relational database modelling.

"**What's the first normal form?**", I hear the sane among you ask.

This is the simplest and most straightforward level which defines what
are normally called "records" (or *rows*).

A record is a defined collection of properties/attributes (*columns*),
where you know roughly what to expect in each property/attribute, and
can access them by some kind of descriptor (i.e., the attribute name).
This is distinct from a *heirarchy*, which is a structured but largely
unknown quantity of data.

Think that document stores are a groundbreaking innovation and step
forward?  Actually, data storage systems of the 1960's were basically
document stores, and it was problems in the practice of this that led
to the principles of ACID, entity relationships and finally the
"purity" of relational OLTP databases.

Didn't know that history?  I'm sorry that as an industry we're
repeating it.  But that's where we are today, and there's really no
point in trying to fit the summit of the last technology cycle to
today's currency of JSON REST APIs, sharded stores and eventually
consistent systems.  Let's make the most of the situation, declare our
facts and repeat the process of rational discovery of problem domains
known as "normalization", with faster machines, more memory and
networked clusters faster than local disks.

So, this is why I chose the name for the module, and ``Record`` as the
name for the base class, but python already has a name for its
attributes, so those are simply ``Property``.

What's wrong with ``collections.namedtuple``?  Or regular python objects?
-------------------------------------------------------------------------

The main answer is type information, which enables more
meta-programming.

You can (but don't have to) declare what type to expect inside each
property that you declare.  This capability, along with *property
traits*, leads to the ability to, for instance, interpret a data
structure and match it against expected types.  This process is
similar to validation, but it turns out that validation as well as a
number of common operations performed on data structures are all types
of *visitor* functions.

Now, to be fair, a lot of this is already possible in Python.  Python
already ships with a good amount of metaclass framework built in.  The
``type()`` keyword is great.  However, certain classes of visitor
functions want to be able to get this from classes without an actual
instance to inspect.

What's wrong with ``schematics``?
---------------------------------

Not a whole lot.  This module started because I turned my nose up at
the explicit "validate" step in schematics, the fact that the JSON API
was baked into the core classes (euphamised as a "primitive" data
API), and that it didn't support some of the core features of python
descriptors.

In fact, it's fair to say that what started out as a refactor of the
descriptor classes in an internal equivalent of schematics turned into
an open source release when we realized that my changes weren't quite
drop-in compatible enough to switch our internal code base all at once
to it.

The "attribute traits" feature, I really like and this is a big
difference between the two modules.  The "required", "coerce", "isa"
and "check" attribute features, blatantly stolen from a Perl module
that in turn (allegedly) stole them from Smalltalk, represent a
difference in focus and an obsession with falling back to type theory
for ideas, even if the result is far from being as declarative and
insanely powerful as ML.

All in all, though, these are quite minor differences, and probably
most people would prefer the stability and larger community
surrounding ``schematics`` to this type-theory heavy package.


So, what is ``normalize``, really?
----------------------------------

It's a general purpose declarative class builder and meta-programming
framework, which just happens to ship with JSON marshalling.

Meta-programming frameworks might not be needed for every problem, but
they crop up all over the place: validation libraries, database
mappings & ORM's, API definitions and implementations, etc.
It would be nice if they could all use the same definition and
mappings could be built out separately.

To enable this, this library's guiding principle is that base class
and metaclasses should be as clean as possible.
No ``to_json`` on all objects unless you specifically inherit from
the ``JsonRecord`` class, for instance.

But the ``to_json`` function which it does ship with uses the
visitor/meta-programming API, such that it can even work on classes
that don't inherit ``JsonRecord``.

What about higher normalization forms?  3NF etc?
------------------------------------------------

While there is some notion of primary keys in the module, mainly for
the purposes of recognizing objects in collections for comparison,
higher levels of normalization are an exercise left to the
implementer.  It's highly unlikely such features will be built into
this package unless they really, really are the right thing for all
conceivable use cases.
