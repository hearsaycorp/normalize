
Referring to components of Records - ``normalize.selector``
===========================================================

There are two main purposes of ``normalize.selector``:

* to abstract *expressions* to individual fields within objects, so
  that the result from a :py:meth:`normalize.diff.diff` operation can
  specify the field where the difference(s) were discovered.

* to *aggregate* collections of these expressions, so that *filters*
  can be created.

Other functions exist, such as the ability for the fields referred to
by selectors to be updated (see :py:meth:`FieldSelector.put`), perhaps
even with auto-vivification of intermediate records and collection
items (:py:meth:`FieldSelector.post`).

Class reference
---------------

.. autoclass:: normalize.selector.FieldSelector
   :members:
   :special-members: __init__, __getnewargs__, __eq__, __ne__, __lt__, __str__, __repr__, __add__, __len__, __getitem__

.. autoclass:: normalize.selector.MultiFieldSelector
   :members: get, __init__, __iter__, __repr__, __str__, __getitem__, __contains__

