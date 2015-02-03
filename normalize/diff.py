#
# This file is a part of the normalize python library
#
# normalize is free software: you can redistribute it and/or modify
# it under the terms of the MIT License.
#
# normalize is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# MIT License for more details.
#
# You should have received a copy of the MIT license along with
# normalize.  If not, refer to the upstream repository at
# http://github.com/hearsaycorp/normalize
#

from __future__ import absolute_import

import collections
from itertools import chain
from itertools import product
import re
import types
import unicodedata

from richenum import OrderedRichEnum
from richenum import OrderedRichEnumValue

from normalize.property import SafeProperty
from normalize.coll import Collection
from normalize.coll import ListCollection
import normalize.exc as exc
from normalize.record import Record
from normalize.record import record_id
from normalize.selector import FieldSelector
from normalize.selector import MultiFieldSelector


class DiffTypes(OrderedRichEnum):
    """
    A :py:class:`richenum.OrderedRichEnum` type to denote the type of an
    individual difference.
    """
    class EnumValue(OrderedRichEnumValue):
        pass

    NO_CHANGE = EnumValue(1, "none", "UNCHANGED")
    ADDED = EnumValue(2, "added", "ADDED")
    REMOVED = EnumValue(3, "removed", "REMOVED")
    MODIFIED = EnumValue(4, "modified", "MODIFIED")


def _coerce_diff(dt):
    if not isinstance(dt, OrderedRichEnumValue):
        if isinstance(dt, (int, long)):
            dt = DiffTypes.from_index(dt)
        else:
            dt = DiffTypes.from_canonical(dt)
    return dt


class DiffInfo(Record):
    """
    Container for storing diff information that can be used to reconstruct the
    values diffed.
    """
    diff_type = SafeProperty(
        coerce=_coerce_diff,
        isa=DiffTypes.EnumValue,
        required=True,
        doc="Enumeration describing the type of difference; a "
            ":py:class:`DiffType` value.")
    base = SafeProperty(
        isa=FieldSelector,
        required=True,
        doc="A FieldSelector object referring to the location within the "
            "base object that the changed field was found.  If the "
            "``diff_type`` is ``DiffTypes.ADDED``, then this will be the "
            "location of the record the field was added in, not the "
            "(non-existant) field itself.",
    )
    other = SafeProperty(
        isa=FieldSelector,
        required=True,
        doc="A FieldSelector object referring to the location within the "
            "'other' object that the changed field was found.  If the "
            "``diff_type`` is ``DiffTypes.REMOVED``, then this will be "
            "location of the record the field was removed from, not the "
            "(non-existant) field itself.",
    )

    def __str__(self):
        if self.base.path != self.other.path:
            pathinfo = (
                self.base.path if (
                    len(self.base) > len(self.other) and
                    self.base.startswith(self.other)
                ) else self.other.path if (
                    len(self.other) > len(self.base) and
                    self.other.startswith(self.base)
                ) else "(%s/%s)" % (self.base.path, self.other.path)
            )
        else:
            pathinfo = self.other.path
        difftype = self.diff_type.display_name
        return "<DiffInfo: %s %s>" % (difftype, pathinfo)


class _Nothing(object):
    def __repr__(self):
        return "(not set)"


_nothing = _Nothing()


class DiffOptions(object):
    """Optional data structure to pass diff options down.  Some functions are
    delegated to this object, allowing for further customization of operation,
    forming the *DiffOptions sub-class API*.
    """
    _nothing = _nothing

    def __init__(self, ignore_ws=True, ignore_case=False,
                 unicode_normal=True, unchanged=False,
                 ignore_empty_slots=False,
                 duck_type=False, extraneous=False,
                 compare_filter=None, fuzzy_match=True,
                 ignore_control_chars=True):
        """Create a new ``DiffOptions`` instance.

        args:

            ``ignore_ws=``\ *BOOL*
                Ignore whitespace in strings (beginning, end and middle).
                True by default.

            ``ignore_case=``\ *BOOL*
                Ignore case differences in strings.  False by default.

            ``ignore_control_chars=``\ *BOOL*
                Ignore control characters in strings.  True by default.

            ``unicode_normal=``\ *BOOL*
                Ignore unicode normal form differences in strings by
                normalizing to NFC before comparison.  True by default.

            ``unchanged=``\ *BOOL*
                Yields ``DiffInfo`` objects for every comparison, not just
                those which found a difference.  Defaults to False.  Useful for
                testing.

            ``ignore_empty_slots=``\ *BOOL*
                If true, slots containing typical 'empty' values (by default,
                just ``''`` and ``None``) are treated as if they were not set.
                False by default.

            ``duck_type=``\ *BOOL*
                Normally, types must match or the result will always be
                :py:attr:`normalize.diff.DiffTypes.MODIFIED` and the comparison
                will not descend further.

                However, setting this option bypasses this check, and just
                checks that the 'other' object has all of the properties
                defined on the 'base' type.  This can be used to check progress
                when porting from other object systems to normalize.

            ``fuzzy_match=``\ *BOOL*
                Enable approximate matching of items in collections, so that
                finer granularity of changes are available.

            ``compare_filter=``\ *MULTIFIELDSELECTOR*\ \|\ *LIST_OF_LISTS*
                Restrict comparison to the fields described by the passed
                :py:class:`MultiFieldSelector` (or list of FieldSelector
                lists/objects)
        """
        self.ignore_ws = ignore_ws
        self.ignore_case = ignore_case
        self.ignore_empty_slots = ignore_empty_slots
        self.ignore_control_chars = ignore_control_chars
        self.unicode_normal = unicode_normal
        self.fuzzy_match = fuzzy_match
        self.unchanged = unchanged
        self.duck_type = duck_type
        self.extraneous = extraneous
        if isinstance(compare_filter, (MultiFieldSelector, types.NoneType)):
            self.compare_filter = compare_filter
        else:
            self.compare_filter = MultiFieldSelector(*compare_filter)

    def items_equal(self, a, b):
        """Sub-class hook which performs value comparison.  Only called for
        comparisons which are not Records."""
        return a == b

    def normalize_control_chars(self, value):
        """Normalizes control and format chars; called if
        ``ignore_control_chars`` is true."""
        if isinstance(value, unicode):
            # The control-chars list below was precomputed with all
            # characters in the [Cc] (Control) and [Cf] (Format)
            # unicode categories.
            # http://www.fileformat.info/info/unicode/category/
            # Code used:
            # all_chars = (unichr(i) for i in xrange(0x110000))
            # control_chars = ''.join(
            #     c for c in all_chars if unicodedata.category(c) in ['Cc', 'Cf']
            # )
            control_chars = (
                u'\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f'
                u'\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d'
                u'\x1e\x1f\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a'
                u'\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99'
                u'\x9a\x9b\x9c\x9d\x9e\x9f\xad\u0600\u0601\u0602\u0603\u06dd'
                u'\u070f\u17b4\u17b5\u200b\u200c\u200d\u200e\u200f\u202a\u202b'
                u'\u202c\u202d\u202e\u2060\u2061\u2062\u2063\u2064\u206a\u206b'
                u'\u206c\u206d\u206e\u206f\ufeff\ufff9\ufffa\ufffb\U000110bd'
                u'\U0001d173\U0001d174\U0001d175\U0001d176\U0001d177\U0001d178'
                u'\U0001d179\U0001d17a\U000e0001\U000e0020\U000e0021\U000e0022'
                u'\U000e0023\U000e0024\U000e0025\U000e0026\U000e0027\U000e0028'
                u'\U000e0029\U000e002a\U000e002b\U000e002c\U000e002d\U000e002e'
                u'\U000e002f\U000e0030\U000e0031\U000e0032\U000e0033\U000e0034'
                u'\U000e0035\U000e0036\U000e0037\U000e0038\U000e0039\U000e003a'
                u'\U000e003b\U000e003c\U000e003d\U000e003e\U000e003f\U000e0040'
                u'\U000e0041\U000e0042\U000e0043\U000e0044\U000e0045\U000e0046'
                u'\U000e0047\U000e0048\U000e0049\U000e004a\U000e004b\U000e004c'
                u'\U000e004d\U000e004e\U000e004f\U000e0050\U000e0051\U000e0052'
                u'\U000e0053\U000e0054\U000e0055\U000e0056\U000e0057\U000e0058'
                u'\U000e0059\U000e005a\U000e005b\U000e005c\U000e005d\U000e005e'
                u'\U000e005f\U000e0060\U000e0061\U000e0062\U000e0063\U000e0064'
                u'\U000e0065\U000e0066\U000e0067\U000e0068\U000e0069\U000e006a'
                u'\U000e006b\U000e006c\U000e006d\U000e006e\U000e006f\U000e0070'
                u'\U000e0071\U000e0072\U000e0073\U000e0074\U000e0075\U000e0076'
                u'\U000e0077\U000e0078\U000e0079\U000e007a\U000e007b\U000e007c'
                u'\U000e007d\U000e007e\U000e007f'
            )
            control_char_re = re.compile('[%s]' % re.escape(control_chars))
            return control_char_re.sub('', value)
        else:
            return "".join([i for i in value if 31 < ord(i) < 127])

    def normalize_whitespace(self, value):
        """Normalizes whitespace; called if ``ignore_ws`` is true."""
        if isinstance(value, unicode):
            return u" ".join(
                x for x in re.split(r'\s+', value, flags=re.UNICODE) if
                len(x)
            )
        else:
            return " ".join(value.split())

    def normalize_unf(self, value):
        """Normalizes Unicode Normal Form (to NFC); called if
        ``unicode_normal`` is true."""
        if isinstance(value, unicode):
            return unicodedata.normalize('NFC', value)
        else:
            return value

    def normalize_case(self, value):
        """Normalizes Case (to upper case); called if ``ignore_case`` is
        true."""
        # FIXME: this will do the wrong thing for letters in some languages, eg
        # Greek, Turkish.  Correct, locale-dependent unicode case folding is
        # left as an exercise for a subclass.
        return value.upper()

    def value_is_empty(self, value):
        """This method decides whether the value is 'empty', and hence the same
        as not specified.  Called if ``ignore_empty_slots`` is true.  Checking
        the value for emptiness happens *after* all other normalization.
        """
        return (not value and isinstance(value, (basestring, types.NoneType)))

    def normalize_text(self, value):
        """This hook is called by :py:meth:`DiffOptions.normalize_val` if the
        value (after slot/item normalization) is a string, and is responsible
        for calling the various ``normalize_``\ foo methods which act on text.
        """
        if self.ignore_control_chars:
            value = self.normalize_control_chars(value)
        if self.ignore_ws:
            value = self.normalize_whitespace(value)
        if self.ignore_case:
            value = self.normalize_case(value)
        if self.unicode_normal:
            value = self.normalize_unf(value)
        return value

    def normalize_val(self, value=_nothing):
        """Hook which is called on every value before comparison, and should
        return the scrubbed value or ``self._nothing`` to indicate that the
        value is not set.
        """
        if isinstance(value, basestring):
            value = self.normalize_text(value)
        if self.ignore_empty_slots and self.value_is_empty(value):
            value = _nothing
        return value

    def normalize_slot(self, value=_nothing, prop=None):
        """Hook which is called on every *record slot*; this is a way to
        perform context-aware clean-ups.

        args:

            ``value=``\ *nothing*\ \|\ *anything*
                The value in the slot.  *nothing* can be detected in sub-class
                methods as ``self._nothing``.

            ``prop=``\ *PROPERTY*
                The slot's :py:class:`normalize.property.Property` instance.
                If this instance has a ``compare_as`` method, then that method
                is called to perform a clean-up before the value is passed to
                ``normalize_val``

        """
        return self.normalize_val(value)

    def normalize_object_slot(self, value=_nothing, prop=None, obj=None):
        """This hook wraps ``normalize_slot``, and performs clean-ups which
        require access to the object the slot is in as well as the value.
        """
        if value is not _nothing and hasattr(prop, "compare_as"):
            method, nargs = getattr(prop, "compare_as_info", (False, 1))
            args = []
            if method:
                args.append(obj)
            if nargs:
                args.append(value)
            value = prop.compare_as(*args)
        return self.normalize_slot(value, prop)

    def normalize_item(self, value=_nothing, coll=None, index=None):
        """Hook which is called on every *collection item*; this is a way to
        perform context-aware clean-ups.

        args:

            ``value=``\ *nothing*\ \|\ *anything*
                The value in the collection slot.  *nothing* can be detected in
                sub-class methods as ``self._nothing``.

            ``coll=``\ *COLLECTION*
                The parent :py:class:`normalize.coll.Collection` instance.  If
                this instance has a ``compare_item_as`` method, then that
                method is called to perform a clean-up before the value is
                passed to ``normalize_val``

            ``index=``\ *HASHABLE*
                The key of the item in the collection.
        """
        if value is not _nothing and hasattr(coll, "compare_item_as"):
            value = coll.compare_item_as(value)
        return self.normalize_val(value)

    def record_id(self, record, type_=None, selector=None):
        """Retrieve an object identifier from the given record; if it is an
        alien class, and the type is provided, then use duck typing to get the
        corresponding fields of the alien class."""
        pk = record_id(record, type_, selector, self.normalize_object_slot)
        return pk

    def id_args(self, type_, fs):
        options = dict()
        if self.duck_type:
            options['type_'] = type_
        if self.compare_filter:
            if len(fs):
                options['selector'] = self.compare_filter[fs][any]
            else:
                options['selector'] = self.compare_filter[any]
        return options

    def is_filtered(self, prop, fs):
        if not self.extraneous and prop.extraneous:
            return True
        return self.compare_filter and fs not in self.compare_filter


def compare_record_iter(a, b, fs_a=None, fs_b=None, options=None):
    """This generator function compares a record, slot by slot, and yields
    differences found as ``DiffInfo`` objects.

    args:

        ``a=``\ *Record*
            The base object

        ``b=``\ *Record*\ \|\ *object*
            The 'other' object, which must be the same type as ``a``, unless
            ``options.duck_type`` is set.

        ``fs_a=``\ *FieldSelector\*
            The current diff context, prefixed to any returned ``base`` field
            in yielded ``DiffInfo`` objects.  Defaults to an empty
            FieldSelector.

        ``fs_b=``\ *FieldSelector\*
            The ``other`` object context.  This will differ from ``fs_a`` in
            the case of collections, where a value has moved slots.  Defaults
            to an empty FieldSelector.

        ``options=``\ *DiffOptions\*
            A constructed ``DiffOptions`` object; a default one is created if
            not passed in.
    """
    if not options:
        options = DiffOptions()

    if not options.duck_type and type(a) != type(b) and not (
        a is _nothing or b is _nothing
    ):
        raise TypeError(
            "cannot compare %s with %s" % (type(a).__name__, type(b).__name__)
        )

    if fs_a is None:
        fs_a = FieldSelector(tuple())
        fs_b = FieldSelector(tuple())

    properties = (
        type(a).properties if a is not _nothing else type(b).properties
    )
    for propname in sorted(properties):

        prop = properties[propname]

        if options.is_filtered(prop, fs_a + propname):
            continue

        propval_a = options.normalize_object_slot(
            getattr(a, propname, _nothing), prop, a,
        )
        propval_b = options.normalize_object_slot(
            getattr(b, propname, _nothing), prop, b,
        )

        if propval_a is _nothing and propval_b is _nothing:
            # don't yield NO_CHANGE for fields missing on both sides
            continue

        one_side_nothing = (propval_a is _nothing) != (propval_b is _nothing)
        types_match = type(propval_a) == type(propval_b)
        comparable = (
            isinstance(propval_a, COMPARABLE) or
            isinstance(propval_b, COMPARABLE)
        )
        prop_fs_a = fs_a + [propname]
        prop_fs_b = fs_b + [propname]

        if comparable and (
            types_match or options.duck_type or (
                options.ignore_empty_slots and one_side_nothing
            )
        ):
            if one_side_nothing:
                diff_types_found = set()

            for type_union, func in COMPARE_FUNCTIONS.iteritems():
                if isinstance(propval_a, type_union) or one_side_nothing and (
                    isinstance(propval_b, type_union)
                ):
                    for diff in func(
                        propval_a, propval_b, prop_fs_a,
                        prop_fs_b, options,
                    ):
                        if one_side_nothing:
                            if diff.diff_type != DiffTypes.NO_CHANGE:
                                diff_types_found.add(diff.diff_type)
                        else:
                            yield diff

            if one_side_nothing:
                net_diff = None
                if diff_types_found:
                    assert(len(diff_types_found) == 1)
                    net_diff = tuple(diff_types_found)[0]
                elif options.unchanged:
                    net_diff = DiffTypes.NO_CHANGE
                if net_diff:
                    yield DiffInfo(
                        diff_type=net_diff,
                        base=prop_fs_a,
                        other=prop_fs_b,
                    )

        elif one_side_nothing:
            yield DiffInfo(
                diff_type=(
                    DiffTypes.ADDED if propval_a is _nothing else
                    DiffTypes.REMOVED
                ),
                base=fs_a + [propname],
                other=fs_b + [propname],
            )

        elif not options.items_equal(propval_a, propval_b):
            yield DiffInfo(
                diff_type=DiffTypes.MODIFIED,
                base=fs_a + [propname],
                other=fs_b + [propname],
            )

        elif options.unchanged:
            yield DiffInfo(
                diff_type=DiffTypes.NO_CHANGE,
                base=fs_a + [propname],
                other=fs_b + [propname],
            )


def collection_generator(collection):
    """This function returns a generator which iterates over the collection,
    similar to Collection.itertuples().  Collections are viewed by this module,
    regardless of type, as a mapping from an index to the value.  For sets, the
    "index" is the value itself (ie, (V, V)).  For dicts, it's a string, and
    for lists, it's an int.

    In general, this function defers to ``itertuples`` and/or ``iteritems``
    methods defined on the instances; however, when duck typing, this function
    typically provides the generator.
    """
    if collection is _nothing:

        def generator():
            if False:
                yield any

    elif hasattr(collection, "itertuples"):
        return collection.itertuples()
    elif hasattr(collection, "iteritems"):
        return collection.iteritems()
    elif hasattr(collection, "__getitem__"):

        def generator():
            i = 0
            for item in collection:
                yield (i, item)
                i += 1

    else:

        def generator():
            for item in collection:
                yield (item, item)

    return generator()


def _nested_falsy(x):
    if isinstance(x, tuple):
        return not all(not _nested_falsy(y) for y in x)
    else:
        return x is _nothing or not x


def _fuzzy_match(set_a, set_b):
    seen = dict()
    scores = list()

    # Yes, this is O(n.m), but python's equality operator is
    # fast for hashable types.
    for a_pk_seq, b_pk_seq in product(set_a, set_b):
        a_pk, a_seq = a_pk_seq
        b_pk, b_seq = b_pk_seq
        if (a_pk, b_pk) in seen:
            if seen[a_pk, b_pk][0]:
                score = list(seen[a_pk, b_pk])
                scores.append(score + [a_pk_seq, b_pk_seq])
        else:
            match = 0
            common = min((len(a_pk), len(b_pk)))
            no_match = max((len(a_pk), len(b_pk))) - common
            for i in range(0, common):
                if a_pk[i] == b_pk[i]:
                    if not _nested_falsy(a_pk[i]):
                        match += 1
                else:
                    no_match += 1
            seen[a_pk, b_pk] = (match, no_match)
            if match:
                scores.append([match, no_match, a_pk_seq, b_pk_seq])

    remaining_a = set(set_a)
    remaining_b = set(set_b)

    for match, no_match, a_pk_seq, b_pk_seq in sorted(
        scores,
        key=lambda x: x[0] - x[1],
        reverse=True,
    ):
        if a_pk_seq in remaining_a and b_pk_seq in remaining_b:
            remaining_a.remove(a_pk_seq)
            remaining_b.remove(b_pk_seq)
            yield a_pk_seq, b_pk_seq

        if not remaining_a or not remaining_b:
            break


# There's a lot of repetition in the following code.  It could be served by one
# function instead of 3, which would be 3 times fewer places to have bugs, but
# it would probably also be more than 3 times as difficult to debug.
def compare_collection_iter(propval_a, propval_b, fs_a=None, fs_b=None,
                            options=None):
    """Generator function to compare two collections, and yield differences.
    This function does not currently report moved items in collections, and
    uses the :py:meth:`DiffOptions.record_id` method to decide if objects are
    to be considered the same, and differences within returned.

    Arguments are the same as :py:func:`compare_record_iter`.

    Note that ``diff_iter`` and ``compare_record_iter`` will call *both* this
    function and ``compare_record_iter`` on ``RecordList`` types.  However, as
    most ``RecordList`` types have no extra properties, no differences are
    yielded by the ``compare_record_iter`` method.
    """
    if fs_a is None:
        fs_a = FieldSelector(tuple())
        fs_b = FieldSelector(tuple())
    if options is None:
        options = DiffOptions()

    propvals = dict(a=propval_a, b=propval_b)
    values = dict()
    rev_keys = dict()
    compare_values = None
    coll_type = (
        type(propval_a) if propval_a is not _nothing else type(propval_b)
    )
    force_descent = (propval_a is _nothing) or (propval_b is _nothing)
    id_args = options.id_args(coll_type.itemtype, fs_a)
    if 'selector' in id_args and not id_args['selector']:
        # early exit shortcut
        return

    for x in "a", "b":
        propval_x = propvals[x]
        vals = values[x] = set()
        rev_key = rev_keys[x] = dict()

        seen = collections.Counter()

        for k, v in collection_generator(propval_x):
            pk = options.record_id(v, **id_args)
            if compare_values is None:
                # the primary key being a tuple is taken to imply that
                # the value type is a Record, and hence descent is
                # possible.
                compare_values = isinstance(pk, tuple)
            vals.add((pk, seen[pk]))
            rev_key[(pk, seen[pk])] = k
            seen[pk] += 1

    removed = values['a'] - values['b']
    added = values['b'] - values['a']
    common = values['a'].intersection(values['b'])

    if compare_values or force_descent:
        descendable = (removed | added) if force_descent else common

        for pk, seq in descendable:
            if not force_descent or propval_a is not _nothing:
                a_key = rev_keys['a'][pk, seq]
                a_val = propval_a[a_key]
            if not force_descent or propval_b is not _nothing:
                b_key = rev_keys['b'][pk, seq]
                b_val = propval_b[b_key]
            if force_descent:
                if propval_a is _nothing:
                    a_key = b_key
                    a_val = _nothing
                else:
                    b_key = a_key
                    b_val = _nothing
            selector_a = fs_a + a_key
            selector_b = fs_b + b_key
            # FIXME: collections of collections!
            for diff in compare_record_iter(
                a_val, b_val, selector_a, selector_b, options,
            ):
                yield diff

        if not force_descent and options.fuzzy_match:
            for a_pk_seq, b_pk_seq in _fuzzy_match(removed, added):
                removed.remove(a_pk_seq)
                added.remove(b_pk_seq)
                a_key = rev_keys['a'][a_pk_seq]
                a_val = propval_a[a_key]
                b_key = rev_keys['b'][b_pk_seq]
                b_val = propval_b[b_key]
                selector_a = fs_a + a_key
                selector_b = fs_b + b_key
                any_diffs = False
                for diff in compare_record_iter(
                    a_val, b_val, selector_a, selector_b, options,
                ):
                    if diff.diff_type != DiffTypes.NO_CHANGE:
                        any_diffs = True
                    yield diff

                if options.unchanged and not any_diffs:
                    yield DiffInfo(
                        diff_type=DiffTypes.NO_CHANGE,
                        base=fs_a + [a_key],
                        other=fs_b + [b_key],
                    )

    if options.unchanged:
        unchanged = values['a'] & values['b']
        for pk, seq in unchanged:
            a_key = rev_keys['a'][pk, seq]
            b_key = rev_keys['b'][pk, seq]
            yield DiffInfo(
                diff_type=DiffTypes.NO_CHANGE,
                base=fs_a + [a_key],
                other=fs_b + [b_key],
            )

    if not force_descent:
        for pk, seq in removed:
            a_key = rev_keys['a'][pk, seq]
            selector = fs_a + [a_key]
            yield DiffInfo(
                diff_type=DiffTypes.REMOVED,
                base=selector,
                other=fs_b,
            )

        for pk, seq in added:
            b_key = rev_keys['b'][pk, seq]
            selector = fs_b + [b_key]
            yield DiffInfo(
                diff_type=DiffTypes.ADDED,
                base=fs_a,
                other=selector,
            )


def compare_list_iter(propval_a, propval_b, fs_a=None, fs_b=None,
                      options=None):
    """Generator for comparing 'simple' lists when they are encountered.  This
    does not currently recurse further.  Arguments are as per other
    ``compare_``\ *X* functions.
    """
    if fs_a is None:
        fs_a = FieldSelector(tuple())
        fs_b = FieldSelector(tuple())
    if not options:
        options = DiffOptions()
    propvals = dict(a=propval_a, b=propval_b)
    values = dict()
    indices = dict()
    for x in "a", "b":
        propval_x = propvals[x]
        vals = values[x] = set()
        rev_key = indices[x] = dict()
        seen = collections.Counter()
        for i, v in collection_generator(propval_x):
            v = options.normalize_item(
                v, propval_a if options.duck_type else propval_x
            )
            if not v.__hash__:
                v = repr(v)
            if v is not _nothing or not options.ignore_empty_slots:
                vals.add((v, seen[v]))
                rev_key[(v, seen[v])] = i
                seen[v] += 1

    removed = values['a'] - values['b']
    added = values['b'] - values['a']

    if options.unchanged:
        unchanged = values['a'] & values['b']
        for v, seq in unchanged:
            a_idx = indices['a'][v, seq]
            b_idx = indices['b'][v, seq]
            yield DiffInfo(
                diff_type=DiffTypes.NO_CHANGE,
                base=fs_a + [a_idx],
                other=fs_b + [b_idx],
            )

    for v, seq in removed:
        a_key = indices['a'][v, seq]
        selector = fs_a + [a_key]
        yield DiffInfo(
            diff_type=DiffTypes.REMOVED,
            base=selector,
            other=fs_b,
        )

    for v, seq in added:
        b_key = indices['b'][v, seq]
        selector = fs_b + [b_key]
        yield DiffInfo(
            diff_type=DiffTypes.ADDED,
            base=fs_a,
            other=selector,
        )


def compare_dict_iter(propval_a, propval_b, fs_a=None, fs_b=None,
                      options=None):
    """Generator for comparing 'simple' dicts when they are encountered.  This
    does not currently recurse further.  Arguments are as per other
    ``compare_``\ *X* functions.
    """
    if fs_a is None:
        fs_a = FieldSelector(tuple())
        fs_b = FieldSelector(tuple())
    if not options:
        options = DiffOptions()
    propvals = dict(a=propval_a, b=propval_b)
    values = dict()
    rev_keys = dict()
    for x in "a", "b":
        propval_x = propvals[x]
        vals = values[x] = set()
        rev_key = rev_keys[x] = dict()
        seen = collections.Counter()
        for k, v in collection_generator(propval_x):
            v = options.normalize_item(
                v, propval_a if options.duck_type else propval_x
            )
            if not v.__hash__:
                v = repr(v)
            if v is not _nothing or not options.ignore_empty_slots:
                vals.add((v, seen[v]))
                rev_key[(v, seen[v])] = k
                seen[v] += 1

    removed = values['a'] - values['b']
    added = values['b'] - values['a']

    if options.unchanged:
        unchanged = values['a'] & values['b']
        for v, seq in unchanged:
            a_key = rev_keys['a'][v, seq]
            b_key = rev_keys['b'][v, seq]
            yield DiffInfo(
                diff_type=DiffTypes.NO_CHANGE,
                base=fs_a + [a_key],
                other=fs_b + [b_key],
            )

    for v, seq in removed:
        a_key = rev_keys['a'][v, seq]
        selector = fs_a + [a_key]
        yield DiffInfo(
            diff_type=DiffTypes.REMOVED,
            base=selector,
            other=fs_b,
        )

    for v, seq in added:
        b_key = rev_keys['b'][v, seq]
        selector = fs_b + [b_key]
        yield DiffInfo(
            diff_type=DiffTypes.ADDED,
            base=fs_a,
            other=selector,
        )


COMPARE_FUNCTIONS = {
    list: compare_list_iter,
    tuple: compare_list_iter,
    dict: compare_dict_iter,
    Collection: compare_collection_iter,
    Record: compare_record_iter,
}


COMPARABLE = tuple(COMPARE_FUNCTIONS)


def diff_iter(base, other, options=None, **kwargs):
    """Compare a Record with another object (usually a record of the same
    type), and yield differences as :py:class:`DiffInfo` instances.

    args:
        ``base=``\ *Record*
            The 'base' object to compare against.  The enumeration in
            :py:class:`DiffTypes` is relative to this object.

        ``other=``\ *Record*\ \|\ *<object>*
            The 'other' object to compare against.  If ``duck_type`` is not
            true, then it must be of the same type as the ``base``.

        ``**kwargs``
            Specify comparison options: ``duck_type``, ``ignore_ws``, etc.  See
            :py:meth:`normalize.diff.DiffOptions.__init__` for the complete
            list.

        ``options=``\ *DiffOptions instance*
            Pass in a pre-constructed :py:class:`DiffOptions` instance.  This
            may not be specified along with ``**kwargs``.
    """
    if options is None:
        options = DiffOptions(**kwargs)
    elif len(kwargs):
        raise exc.DiffOptionsException()

    generators = []

    for type_union, func in COMPARE_FUNCTIONS.iteritems():
        if isinstance(base, type_union):
            generators.append(func(base, other, options=options))

    if len(generators) == 1:
        return generators[0]
    else:
        return chain(*generators)


class Diff(ListCollection):
    """Container for a list of differences."""
    base_type_name = SafeProperty(isa=str, extraneous=True,
                                  doc="Type name of the source object")
    other_type_name = SafeProperty(
        isa=str, extraneous=True,
        doc="Type name of the compared object; normally the same, unless "
            "the ``duck_type`` option was specified.")
    itemtype = DiffInfo

    def __str__(self):
        what = (
            "%s vs %s" % (self.base_type_name, self.other_type_name) if
            self.base_type_name != self.other_type_name else
            self.base_type_name
        )
        diffstate = collections.defaultdict(list)
        for diff in self:
            if diff.diff_type == DiffTypes.ADDED:
                diffstate["+NEW"].append(diff.other)
            elif diff.diff_type == DiffTypes.REMOVED:
                diffstate["-OLD"].append(diff.base)
            elif diff.diff_type == DiffTypes.MODIFIED:
                if diff.base.path == diff.other.path:
                    diffstate['<>X'].append(diff.base)
                else:
                    diffstate['<->OLD'].append(diff.base)
                    diffstate['<+>NEW'].append(diff.other)
            elif diff.diff_type == DiffTypes.NO_CHANGE:
                diffstate['==X'].append(diff.base)

        prefix_paths = []
        for k, v in diffstate.items():
            prefix_paths.append(
                "{prefix}({paths})".format(
                    prefix=k,
                    paths=MultiFieldSelector(*v).path,
                )
            )

        return "<Diff [{what}]; {n} diff(s){summary}>".format(
            n=len(self),
            what=what,
            summary=(
                ": " + "; ".join(
                    "{prefix}({paths})".format(
                        prefix=k,
                        paths=MultiFieldSelector(*v).path,
                    ) for (k, v) in diffstate.items()
                ) if diffstate else ""
            ),
        )


def diff(base, other, **kwargs):
    """Eager version of :py:func:`diff_iter`, which takes all the same options
    and returns a :py:class:`Diff` instance."""
    return Diff(diff_iter(base, other, **kwargs),
                base_type_name=type(base).__name__,
                other_type_name=type(other).__name__)
