===========================
 the ``normalize`` library
===========================

The ``normalize`` package is primarily for writing "plain old data
structures" to wrap data from network sources (typically JSON) in
python objects, use them in python, and frequently send them back.
It is also a useful generic class builder which can be leveraged for
interesting and powerful meta-programming.

Put simply, you write python classes and declare your assumptions
about the data structures you're dealing with, feed in input data and
you get regular python objects back which have attributes which you
can use naturally.
You can then perform basic operations with the objects, such as make
changes to them and convert them back, or compare them to another
version using the rich comparison API.
You can also construct the objects 'natively' using regular python
keyword/value constructors or by passing a ``dict`` as the first
argument.

It is very similar in scope to the ``remoteobjects`` and
``schematics`` packages on PyPI, and may in time evolve to include all
the features of those packages.

Contents of this manual:

.. toctree::
   :maxdepth: 3

   scope
   intro
   property
   record
   selector
   diff
   visitor
   

Module Exports
==============

It's safest to stick with importing directly from the ``normalize``
top-level namespace.  Useful classes and functions not being here may
be a bug!

.. autosummary::
   :nosignatures:

   normalize.DictCollection
   normalize.exc
   normalize.FieldSelector
   normalize.FieldSelectorException
   normalize.from_json
   normalize.JsonListProperty
   normalize.JsonProperty
   normalize.JsonRecord
   normalize.JsonRecordList
   normalize.LazyProperty
   normalize.ListCollection
   normalize.ListProperty
   normalize.make_property_type
   normalize.MultiFieldSelector
   normalize.Property
   normalize.ROProperty
   normalize.Record
   normalize.RecordList
   normalize.RecordMeta
   normalize.SafeProperty
   normalize.to_json



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

