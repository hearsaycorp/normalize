
Comparing Records - ``normalize.diff``
======================================

Comparing objects can be done using the :py:func:`normalize.diff.diff`
function or :py:func:`normalize.diff.diff_iter`, or by calling the
instance methods: :py:meth:`normalize.record.Record.diff` or
:py:meth:`normalize.record.Record.diff_iter`

The iterative versions return :py:class:`DiffInfo` records, and the
functional version returns a :py:class:`Diff`.  These objects are
instances of :py:class:`Record` and :py:class:`RecordList`.

All of the ``diff`` functions and methods take a single 'other'
object, as well as keyword arguments to customize the diff operation;
these are passed to the :py:class:`DiffOptions` constructor and the
result is passed recursively to itself to compare deeply.  The
exception to this is the keyword argument ``options=``, which
specifies a pre-constructed, perhaps derived ``DiffOptions`` instance.

There are some examples of this in :ref:`intro-to-diff`, and more in
the normalize test suite.

Class reference
---------------

.. autofunction:: normalize.diff.diff

.. autofunction:: normalize.diff.diff_iter

.. autoclass:: normalize.diff.Diff
   :show-inheritance:
   :members: base_type_name, other_type_name, itemtype
   :special-members: __str__

.. autoclass:: normalize.diff.DiffInfo
   :members: base, other, diff_type
   :special-members: __str__

.. autoclass:: normalize.diff.DiffTypes
   :members: NO_CHANGE, ADDED, REMOVED, MODIFIED
   :undoc-members:

.. autoclass:: normalize.diff.DiffOptions
   :members: items_equal, normalize_whitespace, normalize_unf, normalize_case, value_is_empty, normalize_text, normalize_val, normalize_slot, normalize_item, record_id, __init__
   :special-members:

Comparison functions
--------------------

These functions call each other recursively, depending on the value
encountered during walking the base object.  They are documented here
to give insight into the workings of more user-facing APIs such as
``diff``, but should be considered to be implementation details.

.. autofunction:: normalize.diff.compare_record_iter

.. autofunction:: normalize.diff.compare_collection_iter

.. autofunction:: normalize.diff.compare_list_iter

.. autofunction:: normalize.diff.compare_dict_iter


.. autofunction:: normalize.diff.collection_generator
