
Referring to components of Records - ``normalize.selector``
===========================================================

There are two main purposes of ``normalize.selector``:

* to abstract *expressions* to individual fields within objects, so
  that the result from a :py:meth:`normalize.diff.diff` operation can
  specify the field where the difference(s) were discovered.

* to *aggregate* collections of these expressions, so that *sets* of
  attributes can be manipulated

The feature set builds on these basic purposes, starting with
retrieval (see :py:meth:`normalize.selector.FieldSelector.get`),
assignment (see :py:meth:`normalize.selector.FieldSelector.put`),
assignment with auto-vivification of intermediate records and
collection items (:py:meth:`normalize.selector.FieldSelector.post`),
and finally deletion
(:py:meth:`normalize.selector.FieldSelector.delete`).

Multple ``FieldSelector`` objects can be combined, to make a
``MultiFieldSelector``.  It also supports
:py:meth:`normalize.selector.MultiFieldSelector.get` which returns a
"filtered" object,
:py:meth:`normalize.selector.MultiFieldSelector.patch` which can be
used to selectively assign values from one object to another, and
:py:meth:`normalize.selector.MultiFieldSelector.delete`.

The ``MultiFieldSelector`` can be used to restrict the action of
visitor functions (such as :py:func:`normalize.diff.diff` and
:py:class:`normalize.visitor.VisitorPattern`) to compare or visit only
a selection of fields in a data structure.

Class reference
---------------

.. autoclass:: normalize.selector.FieldSelector
   :members:
   :special-members: __init__, __getnewargs__, __eq__, __ne__, __lt__, __str__, __repr__, __add__, __len__, __getitem__

.. autoclass:: normalize.selector.MultiFieldSelector
   :members: get, delete, patch, from_path, path, __init__, __iter__, __repr__, __str__, __getitem__, __contains__

