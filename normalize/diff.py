
from __future__ import absolute_import

import collections
from itertools import chain
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


class DiffTypes(OrderedRichEnum):
    """
    An "enum" to represent types of diffs
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
    )
    base = SafeProperty(isa=FieldSelector, required=True)
    other = SafeProperty(isa=FieldSelector, required=True)

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
    """Optional data structure to pass diff options down"""
    def __init__(self, ignore_ws=True, ignore_case=False,
                 unicode_normal=True, unchanged=False,
                 ignore_empty_slots=False,
                 duck_type=False, extraneous=False):
        self.ignore_ws = ignore_ws
        self.ignore_case = ignore_case
        self.ignore_empty_slots = ignore_empty_slots
        self.unicode_normal = unicode_normal
        self.unchanged = unchanged
        self.duck_type = duck_type
        self.extraneous = extraneous

    def items_equal(self, a, b):
        return a == b

    def normalize_whitespace(self, value):
        if isinstance(value, unicode):
            return u" ".join(
                x for x in re.split(r'\s+', value, flags=re.UNICODE) if
                len(x)
            )
        else:
            return " ".join(value.split())

    def normalize_unf(self, value):
        if isinstance(value, unicode):
            return unicodedata.normalize('NFC', value)
        else:
            return value

    def normalize_case(self, value):
        # FIXME: this will do the wrong thing for letters in some languages, eg
        # Greek, Turkish.  Correct, locale-dependent unicode case folding is
        # left as an exercise for a subclass.
        return value.upper()

    def value_is_empty(self, value):
        return (not value and isinstance(value, (basestring, types.NoneType)))

    def normalize_text(self, value):
        if self.ignore_ws:
            value = self.normalize_whitespace(value)
        if self.ignore_case:
            value = self.normalize_case(value)
        if self.unicode_normal:
            value = self.normalize_unf(value)
        return value

    def normalize_val(self, value=_nothing):
        if isinstance(value, basestring):
            value = self.normalize_text(value)
        if self.ignore_empty_slots and self.value_is_empty(value):
            value = _nothing
        return value

    def normalize_slot(self, value=_nothing, prop=None):
        if value is not _nothing and hasattr(prop, "compare_as"):
            value = prop.compare_as(value)
        return self.normalize_val(value)

    def normalize_item(self, value=_nothing, coll=None):
        if value is not _nothing and hasattr(coll, "compare_item_as"):
            value = coll.compare_item_as(value)
        return self.normalize_val(value)

    def record_id(self, record, type_=None):
        """Retrieve an object identifier from the given record; if it is an
        alien class, and the type is provided, then use duck typing to get the
        corresponding fields of the alien class."""
        pk = getattr(record, "__pk__", None)
        return pk if pk is not None else record_id(record, type_)


def compare_record_iter(a, b, fs_a=None, fs_b=None, options=None):
    if not options:
        options = DiffOptions()

    if not options.duck_type and type(a) != type(b):
        raise TypeError(
            "cannot compare %s with %s" % (type(a).__name__, type(b).__name__)
        )

    if fs_a is None:
        fs_a = FieldSelector(tuple())
        fs_b = FieldSelector(tuple())

    properties = type(a).properties
    for propname in sorted(properties):

        prop = properties[propname]
        if prop.extraneous and not options.extraneous:
            continue

        propval_a = options.normalize_slot(
            getattr(a, propname, _nothing), prop,
        )
        propval_b = options.normalize_slot(
            getattr(b, propname, _nothing), prop,
        )

        if propval_a is _nothing and propval_b is _nothing:
            continue
        elif propval_a is _nothing and propval_b is not _nothing:
            yield DiffInfo(
                diff_type=DiffTypes.ADDED,
                base=fs_a + [propname],
                other=fs_b + [propname],
            )
        elif propval_b is _nothing and propval_a is not _nothing:
            yield DiffInfo(
                diff_type=DiffTypes.REMOVED,
                base=fs_a + [propname],
                other=fs_b + [propname],
            )
        elif (options.duck_type or type(propval_a) == type(propval_b)) \
                and isinstance(propval_a, COMPARABLE):
            for type_union, func in COMPARE_FUNCTIONS.iteritems():
                if isinstance(propval_a, type_union):
                    for diff in func(
                        propval_a, propval_b, fs_a + [propname],
                        fs_b + [propname], options,
                    ):
                        yield diff
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
    "index" is always None.  For dicts, it's a string, and for lists, it's an
    int.
    """
    if hasattr(collection, "itertuples"):
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
                yield (None, item)

    return generator()


# There's a lot of repetition in the following code.  It could be served by one
# function instead of 3, which would be 3 times fewer places to have bugs, but
# it would probably also be more than 3 times as difficult to debug.
def compare_collection_iter(propval_a, propval_b, fs_a=None, fs_b=None,
                            options=None):
    if fs_a is None:
        fs_a = FieldSelector(tuple())
        fs_b = FieldSelector(tuple())
    if options is None:
        options = DiffOptions()

    propvals = dict(a=propval_a, b=propval_b)
    values = dict()
    rev_keys = dict()
    compare_values = None
    typeargs = (type(propval_a).itemtype,) if options.duck_type else ()

    for x in "a", "b":
        propval_x = propvals[x]
        vals = values[x] = set()
        rev_key = rev_keys[x] = dict()

        seen = collections.Counter()

        for k, v in collection_generator(propval_x):
            pk = options.record_id(v, *typeargs)
            if compare_values is None:
                compare_values = isinstance(pk, tuple)
            vals.add((pk, seen[pk]))
            rev_key[(pk, seen[pk])] = k
            seen[pk] += 1

    removed = values['a'] - values['b']
    added = values['b'] - values['a']

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

    if compare_values:
        for pk, seq in values['a'].intersection(values['b']):
            a_key = rev_keys['a'][pk, seq]
            b_key = rev_keys['b'][pk, seq]
            selector_a = fs_a + a_key
            selector_b = fs_b + b_key
            for diff in compare_record_iter(
                propval_a[a_key], propval_b[b_key],
                selector_a, selector_b, options,
            ):
                yield diff


def compare_list_iter(propval_a, propval_b, fs_a=None, fs_b=None,
                      options=None):
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
        i = 0
        for v in propval_x:
            v = options.normalize_item(
                v, propval_a if options.duck_type else propval_x
            )
            if v is not _nothing or not options.ignore_empty_slots:
                vals.add((v, seen[v]))
                rev_key[(v, seen[v])] = i
                seen[v] += 1
            i += 1

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
        for k, v in propval_x.iteritems():
            v = options.normalize_item(
                v, propval_a if options.duck_type else propval_x
            )
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
    """Simplified interface to 'compare_*_iter'"""
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
    """Container for a list of differences"""
    base_type_name = SafeProperty(isa=str, extraneous=True)
    other_type_name = SafeProperty(isa=str, extraneous=True)
    itemtype = DiffInfo

    def __str__(self):
        what = (
            "%s vs %s" % (self.base_type_name, self.other_type_name) if
            self.base_type_name != self.other_type_name else
            self.base_type_name
        )
        return "<Diff [{what}]; {n} item(s)>".format(
            n=len(self),
            what=what,
        )


def diff(base, other, **kwargs):
    """Eager version of diff_iter"""
    return Diff(diff_iter(base, other, **kwargs),
                base_type_name=type(base).__name__,
                other_type_name=type(other).__name__)
